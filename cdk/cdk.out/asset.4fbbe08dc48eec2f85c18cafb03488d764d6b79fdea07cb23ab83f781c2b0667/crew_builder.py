"""
CrewAI 설정 빌더 Lambda 함수
DynamoDB Streams 트리거로 prompt_instance 변경을 감지하여
prompt_meta와 조인한 후 CrewAI YAML 설정을 생성하고 S3에 저장
"""

import json
import os
import boto3
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
PROMPT_INSTANCE_TABLE = os.environ['PROMPT_INSTANCE_TABLE']
CREW_CONFIG_TABLE = os.environ['CREW_CONFIG_TABLE']
CREW_CONFIG_BUCKET = os.environ['CREW_CONFIG_BUCKET']
REGION = os.environ['REGION']

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON으로 변환하는 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

class CrewConfigBuilder:
    """CrewAI 설정 빌더 클래스"""
    
    def __init__(self):
        self.prompt_meta_table = dynamodb.Table(PROMPT_META_TABLE)
        self.prompt_instance_table = dynamodb.Table(PROMPT_INSTANCE_TABLE)
        self.crew_config_table = dynamodb.Table(CREW_CONFIG_TABLE)
        
    def process_stream_records(self, records: List[Dict]) -> None:
        """DynamoDB Streams 레코드를 처리"""
        for record in records:
            try:
                event_name = record['eventName']
                logger.info(f"Processing {event_name} event")
                
                if event_name in ['INSERT', 'MODIFY']:
                    # 새로운 인스턴스 또는 수정된 인스턴스 처리
                    new_image = record['dynamodb'].get('NewImage', {})
                    project_id = new_image.get('projectId', {}).get('S')
                    instance_id = new_image.get('instanceId', {}).get('S')
                    
                    if project_id and instance_id:
                        self.rebuild_crew_config(project_id, instance_id)
                        
                elif event_name == 'REMOVE':
                    # 인스턴스 삭제 시 처리
                    old_image = record['dynamodb'].get('OldImage', {})
                    project_id = old_image.get('projectId', {}).get('S')
                    
                    if project_id:
                        # 해당 프로젝트의 설정을 다시 빌드 (남은 인스턴스들로)
                        self.rebuild_crew_config(project_id)
                        
            except Exception as e:
                logger.error(f"Error processing stream record: {str(e)}")
                continue
    
    def rebuild_crew_config(self, project_id: str, instance_id: Optional[str] = None) -> None:
        """프로젝트의 CrewAI 설정을 다시 빌드"""
        try:
            # 1. 프로젝트의 모든 prompt_meta 카드 조회
            meta_response = self.prompt_meta_table.query(
                KeyConditionExpression='projectId = :pid',
                FilterExpression='attribute_exists(isActive) AND isActive = :active',
                ExpressionAttributeValues={
                    ':pid': project_id,
                    ':active': True
                }
            )
            
            prompt_cards = meta_response.get('Items', [])
            if not prompt_cards:
                logger.info(f"No active prompt cards found for project {project_id}")
                return
            
            # 2. 프로젝트의 모든 prompt_instance 조회
            instance_response = self.prompt_instance_table.query(
                KeyConditionExpression='projectId = :pid',
                ExpressionAttributeValues={':pid': project_id}
            )
            
            instances = instance_response.get('Items', [])
            if not instances:
                logger.info(f"No prompt instances found for project {project_id}")
                return
            
            # 3. 최신 인스턴스 선택 (가장 최근 생성된 것)
            latest_instance = max(instances, key=lambda x: x.get('createdAt', ''))
            
            # 4. 카드와 인스턴스 데이터 조인하여 CrewAI 설정 생성
            crew_config = self.build_crew_config(prompt_cards, latest_instance)
            
            # 5. S3에 YAML 파일로 저장
            s3_key = f"crew-configs/{project_id}/crew_config_{latest_instance['instanceId']}.yaml"
            self.save_crew_config_to_s3(s3_key, crew_config)
            
            # 6. DynamoDB에 설정 메타데이터 저장
            self.save_crew_config_metadata(project_id, latest_instance['instanceId'], s3_key, crew_config)
            
            logger.info(f"Successfully rebuilt crew config for project {project_id}")
            
        except Exception as e:
            logger.error(f"Error rebuilding crew config for project {project_id}: {str(e)}")
            raise
    
    def build_crew_config(self, prompt_cards: List[Dict], instance: Dict) -> Dict:
        """프롬프트 카드와 인스턴스 데이터로 CrewAI 설정 생성"""
        # 카드를 stepOrder로 정렬
        sorted_cards = sorted(prompt_cards, key=lambda x: x.get('stepOrder', 0))
        
        # 인스턴스에서 placeholder 값 추출
        placeholder_values = instance.get('placeholderValues', {})
        
        # 시스템 프롬프트 구성 요소들
        system_components = self.extract_system_components(sorted_cards, placeholder_values)
        
        # CrewAI 설정 구성
        crew_config = {
            'version': '1.0',
            'project_id': instance['projectId'],
            'instance_id': instance['instanceId'],
            'created_at': datetime.utcnow().isoformat(),
            'system_prompt': self.build_system_prompt(system_components),
            'agents': self.build_agents_config(system_components),
            'tasks': self.build_tasks_config(system_components),
            'judge_rules': self.build_judge_rules(system_components),
            'metadata': {
                'total_cards': len(sorted_cards),
                'user_id': instance.get('userId'),
                'token_estimate': self.estimate_tokens(system_components)
            }
        }
        
        return crew_config
    
    def extract_system_components(self, cards: List[Dict], placeholder_values: Dict) -> Dict:
        """카드들에서 시스템 구성 요소 추출"""
        components = {
            'main_instruction': '',
            'role_definition': '',
            'style_guide': '',
            'background_context': '',
            'writer_info': '',
            'guide_rules': '',
            'article_sample': '',
            'placeholders': placeholder_values
        }
        
        for card in cards:
            card_type = card.get('type', 'general')
            content = card.get('content', '')
            
            # placeholder 치환
            for placeholder, value in placeholder_values.items():
                content = content.replace(f'{{{placeholder}}}', str(value))
            
            # 카드 타입별 분류
            if 'instruction' in card_type.lower() or 'main' in card_type.lower():
                components['main_instruction'] += content + '\n\n'
            elif 'role' in card_type.lower():
                components['role_definition'] += content + '\n\n'
            elif 'style' in card_type.lower():
                components['style_guide'] += content + '\n\n'
            elif 'background' in card_type.lower():
                components['background_context'] += content + '\n\n'
            elif 'writer' in card_type.lower():
                components['writer_info'] += content + '\n\n'
            elif 'guide' in card_type.lower():
                components['guide_rules'] += content + '\n\n'
            elif 'sample' in card_type.lower():
                components['article_sample'] += content + '\n\n'
        
        return components
    
    def build_system_prompt(self, components: Dict) -> str:
        """시스템 프롬프트 구성"""
        system_prompt = """### SYSTEM INSTRUCTIONS ###

{main_instruction}

### PROJECT CONTEXT ###
{role_definition}

### STYLE GUIDELINES ###
{style_guide}

### BACKGROUND CONTEXT ###
{background_context}

### WRITER INFORMATION ###
{writer_info}

### OPERATIONAL RULES ###
{guide_rules}

### REFERENCE SAMPLES ###
{article_sample}

### LOGICAL FENCING ###
위 지침을 모두 숙지했습니다. 이제 제공된 모든 규칙과 스타일 가이드를 엄격히 준수하여 작업하겠습니다.
""".format(**components)
        
        return system_prompt.strip()
    
    def build_agents_config(self, components: Dict) -> Dict:
        """에이전트 설정 구성"""
        return {
            'planner': {
                'role': '팀장 (김경제)',
                'goal': '기사 제목 생성 프로젝트 전체 총괄 및 최종 품질 관리',
                'backstory': '20년 경력의 베테랑 편집장으로, 팀원들의 전문성을 조율하여 최적의 결과를 도출합니다.',
                'system_prompt': components['main_instruction']
            },
            'journalist': {
                'role': '경제 전문 기자 (이기자)',
                'goal': '저널리즘 충실형 제목 생성 및 사실 검증',
                'backstory': '경제 분야 10년 경력의 전문 기자로, 정확한 정보 전달과 신뢰성을 최우선으로 합니다.',
                'system_prompt': components['role_definition'] + components['style_guide']
            },
            'seo_expert': {
                'role': 'SEO 전문가 (박에디터)',
                'goal': 'SEO/AEO 최적화형 제목 생성',
                'backstory': '디지털 마케팅 전문가로, 검색엔진 최적화와 독자 도달률 극대화에 특화되어 있습니다.',
                'system_prompt': components['guide_rules']
            },
            'social_strategist': {
                'role': '소셜미디어 전략가 (최소셜)',
                'goal': '클릭유도형 및 소셜미디어 공유형 제목 생성',
                'backstory': '소셜미디어 트렌드와 바이럴 콘텐츠 전문가로, 독자 참여도를 극대화합니다.',
                'system_prompt': components['writer_info']
            },
            'data_analyst': {
                'role': '데이터 분석가 (정데이터)',
                'goal': '제목 성과 예측 및 데이터 기반 검증',
                'backstory': '빅데이터 분석 전문가로, 과거 데이터를 바탕으로 제목의 성과를 예측합니다.',
                'system_prompt': components['background_context']
            }
        }
    
    def build_tasks_config(self, components: Dict) -> Dict:
        """작업 설정 구성"""
        return {
            'analysis_task': {
                'description': '기사 내용을 분석하여 핵심 메시지, 키워드, 타겟 독자층을 파악합니다.',
                'expected_output': '기사 분석 결과 (핵심 메시지, 키워드, 독자층)',
                'agent': 'planner'
            },
            'journalism_titles': {
                'description': '저널리즘 충실형 제목 3개를 생성합니다. 정확성과 신뢰성을 최우선으로 합니다.',
                'expected_output': '저널리즘 충실형 제목 3개',
                'agent': 'journalist'
            },
            'balanced_titles': {
                'description': '균형잡힌 후킹형 제목 3개를 생성합니다. 정보성과 흥미성의 균형을 맞춥니다.',
                'expected_output': '균형잡힌 후킹형 제목 3개',
                'agent': 'journalist'
            },
            'click_titles': {
                'description': '클릭유도형 제목 3개를 생성합니다. 독자의 호기심을 자극합니다.',
                'expected_output': '클릭유도형 제목 3개',
                'agent': 'social_strategist'
            },
            'seo_titles': {
                'description': 'SEO/AEO 최적화형 제목 3개를 생성합니다. 검색엔진 노출을 극대화합니다.',
                'expected_output': 'SEO/AEO 최적화형 제목 3개',
                'agent': 'seo_expert'
            },
            'social_titles': {
                'description': '소셜미디어 공유형 제목 3개를 생성합니다. 소셜미디어 특성에 최적화합니다.',
                'expected_output': '소셜미디어 공유형 제목 3개',
                'agent': 'social_strategist'
            },
            'final_review': {
                'description': '모든 제목을 검토하여 최종 15개 제목을 선별하고 품질을 검증합니다.',
                'expected_output': '최종 15개 제목 (유형별 3개씩)',
                'agent': 'planner'
            }
        }
    
    def build_judge_rules(self, components: Dict) -> Dict:
        """Judge 규칙 구성"""
        return {
            'title_rules': {
                'max_length': 50,
                'min_length': 10,
                'max_count_per_type': 3,
                'total_count': 15,
                'language': 'korean',
                'forbidden_chars': ['#', '@', '$', '%'],
                'required_elements': ['명사', '동사']
            },
            'quality_checks': {
                'readability': 'high',
                'accuracy': 'verified',
                'tone_consistency': 'maintained',
                'keyword_inclusion': 'required'
            },
            'retry_conditions': {
                'max_retries': 3,
                'retry_on_length_violation': True,
                'retry_on_count_violation': True,
                'retry_on_language_violation': True
            }
        }
    
    def estimate_tokens(self, components: Dict) -> int:
        """토큰 수 추정"""
        total_text = ' '.join(components.values()) if isinstance(components, dict) else str(components)
        # 한국어 기준 대략적인 토큰 수 추정 (문자 수 / 2)
        return len(total_text) // 2
    
    def save_crew_config_to_s3(self, s3_key: str, config: Dict) -> None:
        """CrewAI 설정을 S3에 YAML 파일로 저장"""
        try:
            yaml_content = yaml.dump(config, allow_unicode=True, default_flow_style=False)
            
            s3_client.put_object(
                Bucket=CREW_CONFIG_BUCKET,
                Key=s3_key,
                Body=yaml_content.encode('utf-8'),
                ContentType='application/x-yaml',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Crew config saved to S3: s3://{CREW_CONFIG_BUCKET}/{s3_key}")
            
        except Exception as e:
            logger.error(f"Error saving crew config to S3: {str(e)}")
            raise
    
    def save_crew_config_metadata(self, project_id: str, instance_id: str, s3_key: str, config: Dict) -> None:
        """CrewAI 설정 메타데이터를 DynamoDB에 저장"""
        try:
            config_id = f"{project_id}#{instance_id}"
            
            item = {
                'configId': config_id,
                'projectId': project_id,
                'instanceId': instance_id,
                'version': 1,
                's3Key': s3_key,
                'createdAt': datetime.utcnow().isoformat(),
                'status': 'active',
                'tokenEstimate': config['metadata']['token_estimate'],
                'agentCount': len(config['agents']),
                'taskCount': len(config['tasks'])
            }
            
            self.crew_config_table.put_item(Item=item)
            logger.info(f"Crew config metadata saved: {config_id}")
            
        except Exception as e:
            logger.error(f"Error saving crew config metadata: {str(e)}")
            raise

def lambda_handler(event, context):
    """Lambda 핸들러 함수"""
    try:
        logger.info(f"Received event: {json.dumps(event, cls=DecimalEncoder)}")
        
        builder = CrewConfigBuilder()
        
        # DynamoDB Streams 레코드 처리
        if 'Records' in event:
            builder.process_stream_records(event['Records'])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Crew config builder completed successfully',
                'processedRecords': len(event.get('Records', []))
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Error in crew config builder: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 