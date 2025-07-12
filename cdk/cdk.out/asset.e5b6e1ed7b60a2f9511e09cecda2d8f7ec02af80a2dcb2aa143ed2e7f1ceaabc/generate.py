import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import urllib.parse

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
stepfunctions_client = boto3.client('stepfunctions', region_name=os.environ['REGION'])
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN', '')
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', '')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET', '')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
REGION = os.environ['REGION']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions 실행 및 상태 조회 메인 핸들러
    
    - POST /projects/{id}/generate: Step Functions 실행
    - GET /executions/{arn}: 실행 상태 조회
    """
    try:
        logger.info(f"요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        elif http_method == 'POST':
            return start_step_functions_execution(event)
        elif http_method == 'GET':
            return get_execution_status(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return create_error_response(500, f"내부 서버 오류: {str(e)}")

def start_step_functions_execution(event: Dict[str, Any]) -> Dict[str, Any]:
    """Step Functions 실행 시작 (또는 Step Functions가 비활성화된 경우 직접 Bedrock 호출)"""
    try:
        # 요청 데이터 파싱
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        article_text = body.get('article', '').strip()
        
        if not article_text:
            return create_error_response(400, "기사 내용이 필요합니다")
        
        if len(article_text) < 100:
            return create_error_response(400, "기사 내용이 너무 짧습니다 (최소 100자)")
        
        # Step Functions가 비활성화된 경우 직접 Bedrock 호출
        if not STATE_MACHINE_ARN:
            logger.info("Step Functions가 비활성화되어 직접 Bedrock 호출을 사용합니다")
            return generate_title_direct(project_id, article_text)
        
        # Step Functions 실행
        execution_input = {
            'projectId': project_id,
            'article': article_text
        }
        
        execution_name = f"title-gen-{project_id}-{int(datetime.utcnow().timestamp())}"
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps(execution_input)
        )
        
        execution_arn = response['executionArn']
        
        logger.info(f"Step Functions 실행 시작: {execution_arn}")
        
        return {
            'statusCode': 202,  # Accepted
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '제목 생성이 시작되었습니다',
                'executionArn': execution_arn,
                'executionName': execution_name,
                'projectId': project_id,
                'pollUrl': f"/executions/{urllib.parse.quote(execution_arn, safe='')}",
                'startTime': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"Step Functions 실행 실패: {str(e)}")
        return create_error_response(500, f"Step Functions 실행 실패: {str(e)}")

def generate_title_direct(project_id: str, article_text: str) -> Dict[str, Any]:
    """Step Functions 없이 직접 제목 생성"""
    try:
        # 프롬프트 카드 또는 레거시 프롬프트 조회
        prompts = get_project_prompts(project_id)
        
        # 프롬프트가 없는 경우 기본 가이드라인 사용
        if not prompts:
            logger.info("프롬프트가 없어서 기본 가이드라인을 사용합니다")
            combined_prompts = get_default_guidelines()
        else:
            combined_prompts = combine_prompts_for_direct_call(prompts)
        
        # Bedrock 페이로드 생성
        payload = create_bedrock_payload_direct(combined_prompts, article_text)
        
        # Bedrock 모델 호출
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        generated_titles = response_body['content'][0]['text']
        
        # 실행 기록 저장
        execution_id = f"direct-{project_id}-{int(datetime.utcnow().timestamp())}"
        save_execution_result(project_id, execution_id, generated_titles, article_text)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '제목 생성이 완료되었습니다',
                'executionId': execution_id,
                'projectId': project_id,
                'result': generated_titles,
                'mode': 'direct',
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"직접 제목 생성 실패: {str(e)}")
        return create_error_response(500, f"제목 생성 실패: {str(e)}")

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 프롬프트 카드 조회"""
    if not PROMPT_META_TABLE:
        return []
    
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # GSI를 사용하여 stepOrder 순으로 조회
        try:
            response = table.query(
                IndexName='projectId-stepOrder-index',
                KeyConditionExpression='projectId = :projectId',
                FilterExpression='enabled = :enabled',
                ExpressionAttributeValues={
                    ':projectId': project_id,
                    ':enabled': True
                },
                ScanIndexForward=True
            )
            return response.get('Items', [])
        except Exception:
            # GSI 실패 시 기본 테이블 조회
            response = table.query(
                KeyConditionExpression='projectId = :projectId',
                ExpressionAttributeValues={':projectId': project_id}
            )
            return response.get('Items', [])
            
    except Exception as e:
        logger.warning(f"프롬프트 조회 실패: {str(e)}")
        return []

def combine_prompts_for_direct_call(prompts: List[Dict[str, Any]]) -> str:
    """프롬프트 카드들을 결합"""
    combined_text = ""
    
    for prompt in prompts:
        title = prompt.get('title', '')
        category = prompt.get('category', 'Unknown')
        step_order = prompt.get('stepOrder', 0)
        
        # S3에서 프롬프트 텍스트 로드
        prompt_text = ""
        if PROMPT_BUCKET and prompt.get('s3Key'):
            try:
                s3_response = s3_client.get_object(
                    Bucket=PROMPT_BUCKET,
                    Key=prompt['s3Key']
                )
                prompt_text = s3_response['Body'].read().decode('utf-8')
            except Exception as e:
                logger.warning(f"S3에서 프롬프트 로드 실패: {prompt.get('s3Key')}")
                prompt_text = f"[프롬프트 로드 실패: {category}]"
        
        if prompt_text:
            combined_text += f"\n\n=== STEP {step_order}: {title or category.upper()} ===\n{prompt_text}"
    
    return combined_text.strip()

def get_default_guidelines() -> str:
    """기본 제목 생성 가이드라인"""
    return """
=== 서울경제신문 기본 제목 생성 가이드라인 ===

1. 핵심 원칙
- 기사의 핵심 내용을 명확하고 정확하게 전달
- 독자의 관심을 끌 수 있는 임팩트 있는 표현
- 서울경제신문의 신뢰성 있는 톤앤매너 유지
- SEO 최적화를 위한 키워드 포함

2. 제목 유형
- 직설적 제목: 사실을 명확하게 전달하는 제목
- 질문형 제목: 독자의 호기심을 자극하는 질문 형태
- 임팩트 제목: 강한 인상을 주는 임팩트 있는 표현

3. 작성 요령
- 15-25자 내외로 간결하게 작성
- 핵심 키워드를 앞쪽에 배치
- 숫자나 구체적 데이터 활용
- 감정적 어필보다는 사실 중심
- 과장된 표현 지양
"""

def create_bedrock_payload_direct(combined_prompts: str, article_text: str) -> Dict[str, Any]:
    """직접 호출용 Bedrock 페이로드 생성"""
    system_prompt = f"""당신은 서울경제신문의 TITLE-NOMICS AI 제목 생성 시스템입니다.

다음은 제목 생성을 위한 가이드라인과 지침입니다:

{combined_prompts}

위의 지침을 따라서 제목을 생성해주세요.
반드시 JSON 형식으로 응답하고, 다양한 카테고리의 제목을 제공하며, 최종 추천 제목을 선정해주세요."""

    user_prompt = f"""다음 기사 원문에 대해 제목을 생성해주세요.

기사 원문:
{article_text}

다음과 같은 JSON 형식으로 응답해주세요:
{{
  "analysis": {{
    "main_topic": "기사의 핵심 주제",
    "target_audience": "대상 독자층",
    "key_keywords": ["핵심", "키워드", "리스트"],
    "tone": "기사의 톤앤매너"
  }},
  "titles": {{
    "straight": [
      {{"title": "직설적 제목 1", "evaluation": {{"clarity": 85, "impact": 70}}}},
      {{"title": "직설적 제목 2", "evaluation": {{"clarity": 90, "impact": 75}}}}
    ],
    "question": [
      {{"title": "질문형 제목", "evaluation": {{"engagement": 80, "curiosity": 90}}}}
    ],
    "impact": [
      {{"title": "임팩트 제목", "evaluation": {{"shock": 95, "shareability": 85}}}}
    ]
  }},
  "final_recommendation": {{
    "title": "최종 추천 제목",
    "type": "제목 유형",
    "reason": "선정 이유 및 기대 효과"
  }}
}}"""

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ]
    }

def save_execution_result(project_id: str, execution_id: str, result: str, article: str) -> None:
    """실행 결과를 DynamoDB에 저장"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        table.put_item(
            Item={
                'projectId': project_id,
                'executionId': execution_id,
                'result': result,
                'article': article,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'completed',
                'mode': 'direct'
            }
        )
    except Exception as e:
        logger.warning(f"실행 결과 저장 실패: {str(e)}")

def get_execution_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Step Functions 실행 상태 조회"""
    try:
        # URL에서 execution ARN 파싱
        execution_arn = urllib.parse.unquote(event['pathParameters']['executionArn'])
        
        # Step Functions 실행 상태 조회
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        status = response['status']
        
        result = {
            'executionArn': execution_arn,
            'status': status,
            'startDate': response.get('startDate', '').isoformat() if response.get('startDate') else '',
            'stopDate': response.get('stopDate', '').isoformat() if response.get('stopDate') else '',
        }
        
        # 실행 완료된 경우 결과 조회
        if status == 'SUCCEEDED':
            result.update(get_execution_result(execution_arn))
        elif status == 'FAILED':
            result.update(get_execution_error(execution_arn))
        elif status == 'TIMED_OUT':
            result['error'] = '실행 시간이 초과되었습니다'
        elif status == 'ABORTED':
            result['error'] = '실행이 중단되었습니다'
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"실행 상태 조회 실패: {str(e)}")
        return create_error_response(500, f"실행 상태 조회 실패: {str(e)}")

def get_execution_result(execution_arn: str) -> Dict[str, Any]:
    """실행 완료 결과 조회"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        
        response = table.get_item(
            Key={'executionArn': execution_arn}
        )
        
        if 'Item' in response:
            item = response['Item']
            return {
                'conversationId': item.get('conversationId', ''),
                'projectId': item.get('projectId', ''),
                'result': item.get('result', {}),
                'usage': item.get('usage', {}),
                'completedAt': item.get('completedAt', '')
            }
        else:
            # DynamoDB에서 찾을 수 없는 경우 Step Functions에서 직접 조회
            return get_result_from_step_functions(execution_arn)
            
    except Exception as e:
        logger.error(f"실행 결과 조회 실패: {str(e)}")
        return {'error': f'결과 조회 실패: {str(e)}'}

def get_execution_error(execution_arn: str) -> Dict[str, Any]:
    """실행 실패 오류 조회"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        
        response = table.get_item(
            Key={'executionArn': execution_arn}
        )
        
        if 'Item' in response:
            item = response['Item']
            return {
                'error': item.get('error', {}),
                'failedAt': item.get('failedAt', '')
            }
        else:
            # DynamoDB에서 찾을 수 없는 경우 Step Functions에서 직접 조회
            return get_error_from_step_functions(execution_arn)
            
    except Exception as e:
        logger.error(f"실행 오류 조회 실패: {str(e)}")
        return {'error': f'오류 조회 실패: {str(e)}'}

def get_result_from_step_functions(execution_arn: str) -> Dict[str, Any]:
    """Step Functions에서 직접 결과 조회"""
    try:
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        if 'output' in response:
            output = json.loads(response['output'])
            return {
                'result': output.get('result', {}),
                'usage': output.get('usage', {}),
                'completedAt': response.get('stopDate', '').isoformat() if response.get('stopDate') else ''
            }
        
        return {'error': '결과를 찾을 수 없습니다'}
        
    except Exception as e:
        logger.error(f"Step Functions 결과 조회 실패: {str(e)}")
        return {'error': f'Step Functions 결과 조회 실패: {str(e)}'}

def get_error_from_step_functions(execution_arn: str) -> Dict[str, Any]:
    """Step Functions에서 직접 오류 조회"""
    try:
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        error_info = {
            'type': 'EXECUTION_FAILED',
            'message': '실행이 실패했습니다',
            'failedAt': response.get('stopDate', '').isoformat() if response.get('stopDate') else ''
        }
        
        return {'error': error_info}
        
    except Exception as e:
        logger.error(f"Step Functions 오류 조회 실패: {str(e)}")
        return {'error': f'Step Functions 오류 조회 실패: {str(e)}'}

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False)
    } 