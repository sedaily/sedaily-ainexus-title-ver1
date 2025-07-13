import json
import boto3
import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List
import urllib.parse

# Lambda Layer에서 FAISS 가져오기
sys.path.append('/opt/python')

# FAISS 유틸리티 임포트
try:
    from faiss_utils import FAISSManager
except ImportError:
    # 로컬 개발용 폴백
    import sys
    sys.path.append('../utils')
    from faiss_utils import FAISSManager

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
FAISS_BUCKET = os.environ.get('FAISS_BUCKET', '')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.anthropic.claude-3-5-sonnet-20241022-v2:0')
BEDROCK_EMBED_MODEL_ID = os.environ.get('BEDROCK_EMBED_MODEL_ID', 'amazon.titan-embed-text-v1')
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
    """RAG 기반 단계별 제목 생성"""
    try:
        start_time = datetime.utcnow()
        
        # RAG 기반 제목 생성 시도
        if FAISS_BUCKET:
            try:
                result = generate_title_with_rag(project_id, article_text)
                if result:
                    execution_id = f"rag-{project_id}-{int(start_time.timestamp())}"
                    save_execution_result(project_id, execution_id, result['titles'], article_text)
                    
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    return {
                        'statusCode': 200,
                        'headers': get_cors_headers(),
                        'body': json.dumps({
                            'message': 'RAG 기반 제목 생성 완료',
                            'executionId': execution_id,
                            'projectId': project_id,
                            'result': result['titles'],
                            'mode': 'rag',
                            'timestamp': datetime.utcnow().isoformat(),
                            'performance': {
                                'processing_time': processing_time,
                                'prompts_used': result.get('prompts_used', 0),
                                'steps_executed': len(result.get('step_results', {}))
                            },
                            'step_results': result.get('step_results', {})
                        }, ensure_ascii=False)
                    }
            except Exception as e:
                logger.warning(f"RAG 기반 생성 실패, 기본 모드로 전환: {str(e)}")
        
        # 기본 모드로 폴백
        return generate_title_fallback(project_id, article_text, start_time)
        
    except Exception as e:
        logger.error(f"제목 생성 실패: {str(e)}")
        return create_error_response(500, f"제목 생성 실패: {str(e)}")

def generate_title_with_rag(project_id: str, article_text: str) -> Dict[str, Any]:
    """RAG 기반 단계별 제목 생성"""
    try:
        # 1. FAISSManager 초기화
        faiss_manager = FAISSManager(FAISS_BUCKET, REGION)
        
        # 2. 단계별 프롬프트 검색 및 실행
        step_results = {}
        previous_results = {}
        prompts_used = 0
        
        # 6단계 워크플로우 실행
        for step in range(1, 7):  # 6단계 워크플로우
            relevant_prompts = search_prompts_by_step(
                faiss_manager, project_id, article_text, step
            )
            
            if relevant_prompts:
                prompts_used += len(relevant_prompts)
                step_result = execute_step_with_prompts(
                    step, relevant_prompts, article_text, previous_results
                )
                step_results[f'step_{step}'] = step_result
                previous_results[f'step_{step}'] = step_result.get('output', '')
            else:
                logger.warning(f"단계 {step}에 관련 프롬프트가 없습니다.")
        
        # 3. 최종 제목들 생성
        final_titles = generate_final_titles_from_steps(step_results, article_text)
        
        # 순수 데이터 반환 (HTTP 응답 구조 아님)
        return {
            'titles': final_titles,
            'method': 'RAG',
            'step_results': step_results,
            'prompts_used': prompts_used,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"RAG 기반 제목 생성 실패: {str(e)}")
        return None

def generate_title_fallback(project_id: str, article_text: str, start_time: datetime) -> Dict[str, Any]:
    """기본 모드 제목 생성 (기존 로직)"""
    prompts = get_project_prompts(project_id)
    
    if not prompts:
        combined_prompts = get_default_guidelines()
    else:
        combined_prompts = combine_prompts_for_direct_call(prompts)
    
    payload = create_bedrock_payload_direct(combined_prompts, article_text)
    
    response = bedrock_runtime.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps(payload)
    )
    
    response_body = json.loads(response['body'].read())
    generated_titles = response_body['content'][0]['text']
    
    execution_id = f"fallback-{project_id}-{int(start_time.timestamp())}"
    save_execution_result(project_id, execution_id, generated_titles, article_text)
    
    processing_time = (datetime.utcnow() - start_time).total_seconds()
    
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'message': '기본 모드 제목 생성 완료',
            'executionId': execution_id,
            'projectId': project_id,
            'result': generated_titles,
            'mode': 'fallback',
            'timestamp': datetime.utcnow().isoformat(),
            'performance': {
                'processing_time': processing_time,
                'prompts_used': len(prompts)
            }
        }, ensure_ascii=False)
    }

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

def search_prompts_by_step(faiss_manager: FAISSManager, project_id: str, article_text: str, step_order: int) -> List[Dict]:
    """단계별 관련 프롬프트 검색"""
    try:
        # FAISS를 사용한 유사도 검색
        search_results = faiss_manager.search_similar(
            project_id=project_id,
            query_text=article_text,
            top_k=10  # 더 많은 결과를 가져와서 필터링
        )
        
        # 특정 단계의 프롬프트만 필터링
        step_prompts = []
        for result in search_results:
            if result.get('step_order') == step_order and result.get('similarity_score', 0) > 0.5:
                # S3에서 전체 프롬프트 텍스트 로드
                prompt_text = load_prompt_from_s3_fast(result.get('s3_key', ''))
                
                if prompt_text:
                    step_prompts.append({
                        'promptId': result['prompt_id'],
                        'category': result['category'],
                        'title': result.get('title', ''),
                        'text': prompt_text,
                        'similarity_score': result['similarity_score'],
                        'step_order': result['step_order']
                    })
        
        # 유사도 점수 기준으로 정렬
        step_prompts.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        # 상위 3개만 반환
        return step_prompts[:3]
        
    except Exception as e:
        logger.error(f"단계별 프롬프트 검색 실패: {str(e)}")
        return []

def load_prompt_from_s3_fast(s3_key: str) -> str:
    """S3에서 프롬프트 빠르게 로드 (캐싱)"""
    if not s3_key:
        return ""
    
    # 글로벌 캐시 사용 (Lambda 컨테이너 재사용)
    if not hasattr(load_prompt_from_s3_fast, '_cache'):
        load_prompt_from_s3_fast._cache = {}
    
    if s3_key in load_prompt_from_s3_fast._cache:
        return load_prompt_from_s3_fast._cache[s3_key]
    
    try:
        response = s3_client.get_object(
            Bucket=PROMPT_BUCKET,
            Key=s3_key
        )
        text = response['Body'].read().decode('utf-8')
        
        # 캐시에 저장 (최대 50개)
        if len(load_prompt_from_s3_fast._cache) < 50:
            load_prompt_from_s3_fast._cache[s3_key] = text
        
        return text
        
    except Exception as e:
        logger.error(f"S3 로드 실패: {s3_key} - {str(e)}")
        return ""

def execute_step_with_prompts(step_number: int, prompts: List[Dict], article_text: str, previous_results: Dict) -> Dict:
    """단계별 프롬프트 실행"""
    step_configs = {
        1: "역할 및 목표 설정",
        2: "지식 베이스 적용",
        3: "사고 과정 분석",
        4: "스타일 가이드 적용",
        5: "추론 및 검증",
        6: "품질 평가"
    }
    
    # 프롬프트 결합
    combined_prompt = "\n\n".join([p['text'] for p in prompts])
    
    # 컨텍스트 구성
    context_parts = [f"=== {step_configs[step_number]} ==="]
    if previous_results:
        context_parts.append("이전 단계 결과:")
        for key, result in previous_results.items():
            context_parts.append(f"{key}: {result.get('analysis', '')[:200]}...")
    
    context_parts.extend(["\n기사 내용:", article_text[:1000], "\n분석 지침:", combined_prompt])
    
    # Bedrock 호출
    try:
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.6,
                "messages": [{
                    "role": "user",
                    "content": "\n".join(context_parts)
                }]
            })
        )
        
        response_body = json.loads(response['body'].read())
        analysis = response_body['content'][0]['text']
        
        return {
            'step_name': step_configs[step_number],
            'analysis': analysis,
            'output': analysis,  # 다음 단계로 전달될 출력
            'prompts_used': [p['promptId'] for p in prompts]
        }
        
    except Exception as e:
        logger.error(f"단계 {step_number} 실행 실패: {str(e)}")
        return {
            'step_name': step_configs[step_number],
            'analysis': f"단계 실행 중 오류 발생: {str(e)}",
            'output': "",  # 오류 시 빈 출력
            'prompts_used': []
        }

def generate_final_titles_from_steps(step_results: Dict, article_text: str) -> str:
    """단계 결과를 바탕으로 최종 제목 생성"""
    # 단계별 분석 요약
    analysis_summary = []
    for step_key, result in step_results.items():
        analysis_summary.append(f"{result['step_name']}: {result['analysis'][:150]}...")
    
    final_prompt = f"""
단계별 분석 결과:
{"".join(analysis_summary)}

원본 기사:
{article_text[:1500]}

위 분석을 바탕으로 다음 형식으로 제목을 생성하세요:

# 유형별 제목 추천

## 1. 저널리즘 충실형
1. [제목]
2. [제목]
3. [제목]

## 2. 균형잡힌 후킹형
1. [제목]
2. [제목]
3. [제목]

## 3. 클릭유도형
1. [제목]
2. [제목]
3. [제목]

각 제목은 15-30자 내외로 작성하세요.
"""
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "temperature": 0.7,
                "messages": [{"role": "user", "content": final_prompt}]
            })
        )
        
        return json.loads(response['body'].read())['content'][0]['text']
        
    except Exception as e:
        logger.error(f"최종 제목 생성 실패: {str(e)}")
        return "제목 생성 중 오류가 발생했습니다."

def get_default_guidelines() -> str:
    """기본 제목 생성 가이드라인"""
    return """
=== 서울경제신문 제목 작성 가이드라인 ===

• 핵심 내용을 명확하고 정확하게 전달
• 15-30자 내외로 간결하게 작성
• 핵심 키워드를 앞쪽에 배치
• 숫자나 구체적 데이터 활용
• 과장된 표현 지양, 사실 중심
"""

def create_bedrock_payload_direct(combined_prompts: str, article_text: str) -> Dict[str, Any]:
    """기본 모드용 Bedrock 페이로드 생성"""
    
    if combined_prompts.strip():
        system_prompt = f"""당신은 서울경제신문의 전문 제목 작가입니다. 다음 가이드라인을 참고하여 뉴스 제목을 작성해주세요:

{combined_prompts}

반드시 지정된 형식을 정확히 따라 출력하세요."""
    else:
        system_prompt = """당신은 서울경제신문의 전문 제목 작가입니다. 뉴스 기사의 핵심을 정확하고 임팩트 있게 전달하는 제목을 작성해주세요."""

    user_prompt = f"""다음 기사에 대해 유형별 제목을 생성하세요:

{article_text}

# 유형별 제목 추천

## 1. 저널리즘 충실형
1. [제목]
2. [제목]
3. [제목]

## 2. 균형잡힌 후킹형
1. [제목]
2. [제목]
3. [제목]

## 3. 클릭유도형
1. [제목]
2. [제목]
3. [제목]

각 제목은 15-30자 내외로 작성하세요."""

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "temperature": 0.6,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}]
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