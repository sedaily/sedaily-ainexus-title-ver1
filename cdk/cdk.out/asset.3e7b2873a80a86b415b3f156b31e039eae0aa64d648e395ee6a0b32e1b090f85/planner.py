"""
CrewAI 플래너 Lambda 함수
S3에서 CrewAI 설정을 읽어와서 실제 AI 에이전트들을 실행하고
Bedrock을 통해 제목 생성 작업을 수행
"""

import json
import os
import boto3
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal
import re

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])
bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])

# 환경 변수
CREW_CONFIG_BUCKET = os.environ['CREW_CONFIG_BUCKET']
CREW_CONFIG_TABLE = os.environ['CREW_CONFIG_TABLE']
CONVERSATION_TABLE = os.environ['CONVERSATION_TABLE']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']
REGION = os.environ['REGION']

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON으로 변환하는 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

class CrewAIPlanner:
    """CrewAI 플래너 클래스"""
    
    def __init__(self):
        self.crew_config_table = dynamodb.Table(CREW_CONFIG_TABLE)
        self.conversation_table = dynamodb.Table(CONVERSATION_TABLE)
        
    def execute_crew_workflow(self, project_id: str, user_input: str, instance_id: Optional[str] = None) -> Dict:
        """CrewAI 워크플로우 실행"""
        try:
            # 1. 최신 CrewAI 설정 로드
            crew_config = self.load_crew_config(project_id, instance_id)
            if not crew_config:
                raise Exception(f"No crew config found for project {project_id}")
            
            # 2. 시스템 프롬프트 준비
            system_prompt = crew_config['system_prompt']
            
            # 3. Agent 워크플로우 실행 (순차적)
            workflow_results = self.execute_agent_workflow(crew_config, user_input, system_prompt)
            
            # 4. Judge 검증 수행
            validated_results = self.validate_with_judge(workflow_results, crew_config['judge_rules'])
            
            # 5. 결과를 conversation 테이블에 저장
            conversation_id = self.save_conversation_result(project_id, user_input, validated_results)
            
            return {
                'conversationId': conversation_id,
                'results': validated_results,
                'metadata': {
                    'projectId': project_id,
                    'instanceId': crew_config.get('instance_id'),
                    'agentCount': len(crew_config['agents']),
                    'taskCount': len(crew_config['tasks']),
                    'totalTokens': validated_results.get('tokenUsage', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing crew workflow: {str(e)}")
            raise
    
    def load_crew_config(self, project_id: str, instance_id: Optional[str] = None) -> Optional[Dict]:
        """S3에서 CrewAI 설정 로드"""
        try:
            # 1. DynamoDB에서 최신 설정 메타데이터 조회
            if instance_id:
                config_id = f"{project_id}#{instance_id}"
                response = self.crew_config_table.get_item(Key={'configId': config_id})
                
                if 'Item' not in response:
                    return None
                
                s3_key = response['Item']['s3Key']
            else:
                # 최신 설정 조회
                response = self.crew_config_table.query(
                    IndexName='projectId-version-index',
                    KeyConditionExpression='projectId = :pid',
                    ExpressionAttributeValues={':pid': project_id},
                    ScanIndexForward=False,  # 최신순 정렬
                    Limit=1
                )
                
                if not response['Items']:
                    return None
                
                s3_key = response['Items'][0]['s3Key']
            
            # 2. S3에서 YAML 설정 파일 로드
            response = s3_client.get_object(Bucket=CREW_CONFIG_BUCKET, Key=s3_key)
            yaml_content = response['Body'].read().decode('utf-8')
            
            # 3. YAML 파싱
            config = yaml.safe_load(yaml_content)
            logger.info(f"Loaded crew config from S3: {s3_key}")
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading crew config: {str(e)}")
            return None
    
    def execute_agent_workflow(self, crew_config: Dict, user_input: str, system_prompt: str) -> Dict:
        """에이전트 워크플로우 실행 (CrewAI 로직 시뮬레이션)"""
        agents = crew_config['agents']
        tasks = crew_config['tasks']
        
        # 워크플로우 결과 저장
        workflow_results = {
            'userInput': user_input,
            'timestamp': datetime.utcnow().isoformat(),
            'agentResults': {},
            'finalTitles': {},
            'tokenUsage': 0
        }
        
        # 1. 기사 분석 단계 (플래너)
        analysis_result = self.execute_bedrock_call(
            system_prompt + "\n\n" + agents['planner']['system_prompt'],
            f"다음 기사를 분석하여 핵심 메시지, 키워드, 타겟 독자층을 파악해주세요:\n\n{user_input}",
            "기사 분석 결과를 JSON 형태로 제공해주세요."
        )
        
        workflow_results['agentResults']['analysis'] = analysis_result
        workflow_results['tokenUsage'] += analysis_result.get('tokenCount', 0)
        
        # 2. 각 유형별 제목 생성
        title_types = [
            ('journalism', 'journalist', '저널리즘 충실형'),
            ('balanced', 'journalist', '균형잡힌 후킹형'),
            ('click', 'social_strategist', '클릭유도형'),
            ('seo', 'seo_expert', 'SEO/AEO 최적화형'),
            ('social', 'social_strategist', '소셜미디어 공유형')
        ]
        
        for title_type, agent_key, type_name in title_types:
            agent_prompt = system_prompt + "\n\n" + agents[agent_key]['system_prompt']
            
            user_prompt = f"""
기사 분석 결과:
{analysis_result.get('content', '')}

위 분석을 바탕으로 {type_name} 제목 3개를 생성해주세요.

기사 내용:
{user_input}

요구사항:
- 정확히 3개의 제목만 생성
- 각 제목은 50자 이내
- 한국어로 작성
- {type_name}의 특성에 맞게 최적화
"""
            
            title_result = self.execute_bedrock_call(
                agent_prompt,
                user_prompt,
                f"{type_name} 제목 3개를 생성해주세요."
            )
            
            workflow_results['agentResults'][title_type] = title_result
            workflow_results['tokenUsage'] += title_result.get('tokenCount', 0)
            
            # 제목 추출
            titles = self.extract_titles_from_response(title_result.get('content', ''))
            workflow_results['finalTitles'][title_type] = titles
        
        # 3. 최종 검토 단계 (플래너)
        all_titles = []
        for type_key, titles in workflow_results['finalTitles'].items():
            all_titles.extend(titles)
        
        final_review_prompt = f"""
생성된 모든 제목들을 검토하고 최종 15개 제목을 확정해주세요:

{json.dumps(workflow_results['finalTitles'], ensure_ascii=False, indent=2)}

검토 기준:
- 각 유형별로 정확히 3개씩, 총 15개
- 길이 10-50자 준수
- 중복 제거
- 품질 최적화
"""
        
        final_review = self.execute_bedrock_call(
            system_prompt + "\n\n" + agents['planner']['system_prompt'],
            final_review_prompt,
            "최종 15개 제목을 유형별로 정리해주세요."
        )
        
        workflow_results['agentResults']['final_review'] = final_review
        workflow_results['tokenUsage'] += final_review.get('tokenCount', 0)
        
        return workflow_results
    
    def execute_bedrock_call(self, system_prompt: str, user_prompt: str, task_description: str) -> Dict:
        """Bedrock API 호출"""
        try:
            # Claude 메시지 형식으로 구성
            messages = [
                {
                    "role": "user",
                    "content": f"{system_prompt}\n\n{user_prompt}\n\n{task_description}"
                }
            ]
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "temperature": 0.3,
                "top_p": 0.9,
                "messages": messages
            }
            
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            
            result = {
                'content': response_body['content'][0]['text'],
                'tokenCount': response_body['usage']['input_tokens'] + response_body['usage']['output_tokens'],
                'inputTokens': response_body['usage']['input_tokens'],
                'outputTokens': response_body['usage']['output_tokens'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Bedrock call completed. Tokens: {result['tokenCount']}")
            return result
            
        except Exception as e:
            logger.error(f"Error calling Bedrock: {str(e)}")
            return {
                'content': f"Error: {str(e)}",
                'tokenCount': 0,
                'inputTokens': 0,
                'outputTokens': 0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def extract_titles_from_response(self, response_text: str) -> List[str]:
        """AI 응답에서 제목들을 추출"""
        try:
            # 다양한 패턴으로 제목 추출 시도
            patterns = [
                r'1\.\s*(.+)',
                r'2\.\s*(.+)',
                r'3\.\s*(.+)',
                r'-\s*(.+)',
                r'\*\s*(.+)',
                r'●\s*(.+)',
                r'•\s*(.+)'
            ]
            
            titles = []
            lines = response_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        title = match.group(1).strip()
                        # 제목 정제
                        title = re.sub(r'["""''"]', '', title)  # 따옴표 제거
                        title = title.strip('.,!?')  # 마지막 구두점 제거
                        
                        if 5 <= len(title) <= 50 and title not in titles:
                            titles.append(title)
                            break
            
            # 3개 미만이면 원본 텍스트에서 문장 추출
            if len(titles) < 3:
                sentences = re.split(r'[.!?]', response_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if 10 <= len(sentence) <= 50 and sentence not in titles:
                        titles.append(sentence)
                        if len(titles) >= 3:
                            break
            
            return titles[:3]  # 최대 3개만 반환
            
        except Exception as e:
            logger.error(f"Error extracting titles: {str(e)}")
            return [f"제목 추출 오류: {str(e)}"]
    
    def validate_with_judge(self, workflow_results: Dict, judge_rules: Dict) -> Dict:
        """Judge 규칙으로 결과 검증 및 재시도"""
        validated_results = workflow_results.copy()
        
        try:
            title_rules = judge_rules.get('title_rules', {})
            retry_conditions = judge_rules.get('retry_conditions', {})
            
            max_retries = retry_conditions.get('max_retries', 3)
            retry_count = 0
            
            while retry_count < max_retries:
                validation_issues = []
                
                # 각 유형별 제목 검증
                for title_type, titles in validated_results['finalTitles'].items():
                    # 개수 검증
                    if len(titles) != title_rules.get('max_count_per_type', 3):
                        validation_issues.append(f"{title_type}: 제목 개수 {len(titles)}개 (요구: 3개)")
                    
                    # 길이 검증
                    for i, title in enumerate(titles):
                        if len(title) > title_rules.get('max_length', 50):
                            validation_issues.append(f"{title_type}[{i+1}]: 길이 초과 ({len(title)}자)")
                        elif len(title) < title_rules.get('min_length', 10):
                            validation_issues.append(f"{title_type}[{i+1}]: 길이 부족 ({len(title)}자)")
                        
                        # 금지 문자 검증
                        forbidden_chars = title_rules.get('forbidden_chars', [])
                        for char in forbidden_chars:
                            if char in title:
                                validation_issues.append(f"{title_type}[{i+1}]: 금지 문자 '{char}' 포함")
                
                # 전체 제목 수 검증
                total_titles = sum(len(titles) for titles in validated_results['finalTitles'].values())
                if total_titles != title_rules.get('total_count', 15):
                    validation_issues.append(f"전체 제목 수: {total_titles}개 (요구: 15개)")
                
                # 검증 통과시 종료
                if not validation_issues:
                    validated_results['validationStatus'] = 'passed'
                    validated_results['retryCount'] = retry_count
                    break
                
                # 재시도 조건 확인
                retry_count += 1
                logger.warning(f"Validation failed (attempt {retry_count}): {validation_issues}")
                
                if retry_count < max_retries:
                    # 문제가 있는 부분만 재생성
                    self.retry_problematic_titles(validated_results, validation_issues)
                else:
                    # 최대 재시도 횟수 도달
                    validated_results['validationStatus'] = 'failed'
                    validated_results['validationIssues'] = validation_issues
                    validated_results['retryCount'] = retry_count
            
            return validated_results
            
        except Exception as e:
            logger.error(f"Error in judge validation: {str(e)}")
            validated_results['validationStatus'] = 'error'
            validated_results['validationError'] = str(e)
            return validated_results
    
    def retry_problematic_titles(self, workflow_results: Dict, validation_issues: List[str]) -> None:
        """문제가 있는 제목들만 재생성"""
        # 간단한 구현: 길이 문제가 있는 제목들을 수정
        for title_type, titles in workflow_results['finalTitles'].items():
            fixed_titles = []
            for title in titles:
                if len(title) > 50:
                    # 50자로 자르기
                    fixed_title = title[:47] + "..."
                    fixed_titles.append(fixed_title)
                elif len(title) < 10:
                    # 최소 길이 보장 (간단한 확장)
                    fixed_title = title + " - 서울경제신문"
                    fixed_titles.append(fixed_title[:50])
                else:
                    fixed_titles.append(title)
            
            workflow_results['finalTitles'][title_type] = fixed_titles
    
    def save_conversation_result(self, project_id: str, user_input: str, results: Dict) -> str:
        """대화 결과를 DynamoDB에 저장"""
        try:
            conversation_id = f"{project_id}#{int(datetime.utcnow().timestamp() * 1000)}"
            
            item = {
                'projectId': project_id,
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'conversationId': conversation_id,
                'userInput': user_input,
                'aiResponse': json.dumps(results['finalTitles'], ensure_ascii=False),
                'metadata': {
                    'tokenUsage': results.get('tokenUsage', 0),
                    'validationStatus': results.get('validationStatus', 'unknown'),
                    'retryCount': results.get('retryCount', 0),
                    'agentCount': len(results.get('agentResults', {})),
                    'createdAt': datetime.utcnow().isoformat()
                },
                'fullResults': json.dumps(results, ensure_ascii=False, cls=DecimalEncoder)
            }
            
            self.conversation_table.put_item(Item=item)
            logger.info(f"Conversation result saved: {conversation_id}")
            
            return conversation_id
            
        except Exception as e:
            logger.error(f"Error saving conversation result: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda 핸들러 함수"""
    try:
        logger.info(f"Received event: {json.dumps(event, cls=DecimalEncoder)}")
        
        # HTTP 요청 파싱
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = event
        
        # 필수 파라미터 검증
        project_id = body.get('projectId')
        user_input = body.get('userInput') or body.get('message')
        instance_id = body.get('instanceId')
        
        if not project_id or not user_input:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'projectId and userInput are required'
                })
            }
        
        # CrewAI 워크플로우 실행
        planner = CrewAIPlanner()
        results = planner.execute_crew_workflow(project_id, user_input, instance_id)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps(results, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error in planner lambda: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e)
            })
        } 