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
        
        logger.info(f"프로젝트 {project_id}에 대해 {len(prompts)}개의 프롬프트 카드를 찾았습니다")
        for i, prompt in enumerate(prompts):
            logger.info(f"프롬프트 {i+1}: {prompt.get('title', 'No Title')} (stepOrder: {prompt.get('stepOrder', 'N/A')}, s3Key: {prompt.get('s3Key', 'N/A')})")
        
        # 프롬프트가 없는 경우 기본 가이드라인 사용
        if not prompts:
            logger.info("프롬프트가 없어서 기본 가이드라인을 사용합니다")
            combined_prompts = get_default_guidelines()
        else:
            combined_prompts = combine_prompts_for_direct_call(prompts)
            logger.info(f"결합된 프롬프트 길이: {len(combined_prompts)} 문자")
            logger.info(f"결합된 프롬프트 내용 (첫 500자): {combined_prompts[:500]}...")
        
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
                'timestamp': datetime.utcnow().isoformat(),
                'debug': {
                    'promptCount': len(prompts),
                    'usedDefaultGuidelines': len(prompts) == 0,
                    'combinedPromptsLength': len(combined_prompts),
                    'promptTitles': [p.get('title', f"Step {p.get('stepOrder', '?')}") for p in prompts],
                    'firstPromptPreview': combined_prompts[:200] + "..." if len(combined_prompts) > 200 else combined_prompts
                }
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"직접 제목 생성 실패: {str(e)}")
        return create_error_response(500, f"제목 생성 실패: {str(e)}")

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 프롬프트 카드 조회"""
    if not PROMPT_META_TABLE:
        logger.warning("PROMPT_META_TABLE 환경변수가 설정되지 않았습니다")
        return []
    
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        logger.info(f"DynamoDB 테이블 '{PROMPT_META_TABLE}'에서 프로젝트 {project_id}의 프롬프트 조회 시작")
        
        # GSI를 사용하여 stepOrder 순으로 조회
        try:
            logger.info("GSI 'projectId-stepOrder-index'를 사용하여 쿼리 실행")
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
            prompts = response.get('Items', [])
            logger.info(f"GSI 쿼리 결과: {len(prompts)}개의 활성화된 프롬프트 발견")
            return prompts
        except Exception as gsi_error:
            logger.warning(f"GSI 쿼리 실패, 기본 테이블 쿼리로 전환: {str(gsi_error)}")
            # GSI 실패 시 기본 테이블 조회
            response = table.query(
                KeyConditionExpression='projectId = :projectId',
                ExpressionAttributeValues={':projectId': project_id}
            )
            all_prompts = response.get('Items', [])
            # enabled 필터링을 코드에서 수행
            enabled_prompts = [p for p in all_prompts if p.get('enabled', True)]
            logger.info(f"기본 테이블 쿼리 결과: 전체 {len(all_prompts)}개 중 {len(enabled_prompts)}개 활성화됨")
            return enabled_prompts
            
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        return []

def combine_prompts_for_direct_call(prompts: List[Dict[str, Any]]) -> str:
    """프롬프트 카드들을 결합"""
    combined_text = ""
    
    logger.info(f"프롬프트 결합 시작: {len(prompts)}개 카드 처리")
    
    for prompt in prompts:
        title = prompt.get('title', '')
        category = prompt.get('category', 'Unknown')
        step_order = prompt.get('stepOrder', 0)
        s3_key = prompt.get('s3Key', '')
        
        logger.info(f"처리 중: STEP {step_order} - {title} (s3Key: {s3_key})")
        
        # S3에서 프롬프트 텍스트 로드
        prompt_text = ""
        if PROMPT_BUCKET and s3_key:
            try:
                logger.info(f"S3에서 프롬프트 로드 시도: {PROMPT_BUCKET}/{s3_key}")
                s3_response = s3_client.get_object(
                    Bucket=PROMPT_BUCKET,
                    Key=s3_key
                )
                prompt_text = s3_response['Body'].read().decode('utf-8')
                logger.info(f"S3에서 프롬프트 로드 성공: {len(prompt_text)} 문자")
            except Exception as e:
                logger.warning(f"S3에서 프롬프트 로드 실패: {s3_key}, 오류: {str(e)}")
                prompt_text = f"[프롬프트 로드 실패: {category}]"
        else:
            logger.warning(f"S3 정보 누락: PROMPT_BUCKET={PROMPT_BUCKET}, s3Key={s3_key}")
        
        if prompt_text:
            combined_text += f"\n\n=== STEP {step_order}: {title or category.upper()} ===\n{prompt_text}"
            logger.info(f"프롬프트 추가됨: STEP {step_order}")
        else:
            logger.warning(f"프롬프트 텍스트가 비어있음: STEP {step_order}")
    
    logger.info(f"프롬프트 결합 완료: 총 {len(combined_text)} 문자")
    return combined_text.strip()

def get_default_guidelines() -> str:
    """기본 제목 생성 가이드라인 - 속도 최적화된 간결한 버전"""
    return """
=== 서울경제신문 제목 작성 가이드라인 ===

• 핵심 내용을 명확하고 정확하게 전달
• 15-30자 내외로 간결하게 작성
• 핵심 키워드를 앞쪽에 배치
• 숫자나 구체적 데이터 활용
• 과장된 표현 지양, 사실 중심
"""

def create_bedrock_payload_direct(combined_prompts: str, article_text: str) -> Dict[str, Any]:
    """직접 호출용 Bedrock 페이로드 생성 - 속도 최적화된 간결한 형식"""
    
    # 프롬프트가 있는 경우 가이드라인 포함, 없으면 기본 지침만
    if combined_prompts.strip():
        system_prompt = f"""당신은 서울경제신문의 전문 제목 작가입니다. 다음 가이드라인을 참고하여 뉴스 제목을 작성해주세요:

{combined_prompts}

반드시 지정된 형식을 정확히 따라 출력하세요. 추가 설명이나 분석은 절대 포함하지 마세요."""
    else:
        system_prompt = """당신은 서울경제신문의 전문 제목 작가입니다. 뉴스 기사의 핵심을 정확하고 임팩트 있게 전달하는 제목을 작성해주세요. 반드시 지정된 형식만 출력하세요."""

    user_prompt = f"""다음 기사에 대해 아래 형식으로 정확히 출력하세요. 다른 설명이나 분석은 절대 포함하지 마세요:

{article_text}

---

**출력 형식 (반드시 예시와 똑같이 따라하세요):**

# 유형별 제목 추천

## 1. 저널리즘 충실형
1. 윤석열 전 대통령 지지자 450명, 구치소 앞 석방 촉구 집회
★★★★☆ (85점)

2. 서울구치소 앞 윤석열 석방 촉구 집회...경찰 540명 배치
★★★★☆ (82점)

3. 윤석열 지지·반대 단체, 서울구치소 앞 맞불집회 진행
★★★★☆ (80점)

## 2. 균형잡힌 후킹형
1. [제목]
★★★★★ (88점)

2. [제목]
★★★★☆ (85점)

3. [제목]
★★★★☆ (83점)

## 3. 클릭유도형
1. [제목]
★★★★★ (90점)

2. [제목]
★★★★☆ (87점)

3. [제목]
★★★★☆ (85점)

## 4. SEO/AEO 최적화형
1. [제목]
★★★★☆ (86점)

2. [제목]
★★★★☆ (84점)

3. [제목]
★★★★☆ (82점)

## 5. 소셜미디어 공유형
1. [제목]
★★★★★ (92점)

2. [제목]
★★★★☆ (89점)

3. [제목]
★★★★☆ (87점)

**절대 지켜야 할 규칙:**
- 제목과 점수는 반드시 별도 줄에 작성하세요
- 위 예시와 정확히 같은 형식으로 출력하세요
- 점수는 ★★★★★ (점수) 형식으로 별도 줄에 작성하세요
- 각 제목은 15-30자 내외로 작성하세요
- 제목 외에 다른 내용은 출력하지 마세요"""

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,  # 토큰 수 줄여서 속도 향상
        "temperature": 0.5,  # 온도 낮춰서 더 일관된 형식 출력
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