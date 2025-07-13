import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
CHAT_HISTORY_TABLE = os.environ['CHAT_HISTORY_TABLE']
CHAT_SESSION_TABLE = os.environ['CHAT_SESSION_TABLE']
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET', '')
REGION = os.environ['REGION']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']
BEDROCK_SUMMARY_MODEL_ID = os.environ['BEDROCK_SUMMARY_MODEL_ID']

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON 직렬화 가능한 타입으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    간소화된 채팅 라우터 메인 핸들러
    
    Routes:
    - POST /projects/{id}/chat: 채팅 메시지 처리
    - GET /projects/{id}/chat/sessions: 채팅 세션 목록
    - GET /projects/{id}/chat/sessions/{sessionId}: 채팅 히스토리
    - DELETE /projects/{id}/chat/sessions/{sessionId}: 채팅 세션 삭제
    """
    try:
        logger.info(f"채팅 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        elif http_method == 'POST' and '/chat' in path and '/sessions' not in path:
            return handle_chat_message(event)
        elif http_method == 'GET' and '/sessions' in path:
            if event.get('pathParameters', {}).get('sessionId'):
                return get_chat_history(event)
            else:
                return get_chat_sessions(event)
        elif http_method == 'DELETE' and '/sessions' in path:
            return delete_chat_session(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"채팅 요청 처리 중 오류 발생: {str(e)}")
        return create_error_response(500, f"내부 서버 오류: {str(e)}")

def handle_chat_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """채팅 메시지 처리 (간소화된 버전)"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        user_message = body.get('message', '').strip()
        session_id = body.get('sessionId') or str(uuid.uuid4())
        user_id = body.get('userId', 'default')
        
        if not user_message:
            return create_error_response(400, "메시지가 필요합니다")
        
        # 프로젝트 프롬프트 조회
        prompts = get_project_prompts(project_id)
        
        # 채팅 히스토리 조회
        chat_history = get_recent_chat_history(project_id, session_id, user_id)
        
        # 간소화된 채팅 처리
        response = process_chat_simplified(
            project_id, user_message, prompts, chat_history
        )
        
        # 채팅 히스토리 저장
        save_chat_message(project_id, session_id, user_id, user_message, response['message'])
        
        # 세션 메타데이터 업데이트
        update_chat_session(project_id, session_id, user_id)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'sessionId': session_id,
                'projectId': project_id,
                'message': response['message'],
                'usage': response.get('usage', {}),
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': response.get('metadata', {})
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"채팅 메시지 처리 실패: {str(e)}")
        return create_error_response(500, f"채팅 처리 실패: {str(e)}")

def process_chat_simplified(
    project_id: str, 
    user_message: str, 
    prompts: List[Dict[str, Any]], 
    chat_history: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """간소화된 채팅 처리"""
    try:
        # 프롬프트들을 결합하여 시스템 메시지 생성
        system_prompt = build_system_prompt(prompts)
        
        # 채팅 히스토리를 컨텍스트로 변환
        history_context = format_chat_history(chat_history)
        
        # Bedrock 호출을 위한 메시지 구성
        messages = []
        
        if history_context:
            messages.append({
                "role": "user",
                "content": f"이전 대화 맥락:\n{history_context}\n\n현재 질문: {user_message}"
            })
        else:
            messages.append({
                "role": "user",
                "content": user_message
            })
        
        # Bedrock 모델 호출
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": messages
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        ai_message = response_body['content'][0]['text']
        
        return {
            'message': ai_message,
            'usage': response_body.get('usage', {}),
            'metadata': {
                'processing_mode': 'simplified',
                'prompts_loaded': len(prompts),
                'history_entries': len(chat_history)
            }
        }
        
    except Exception as e:
        logger.error(f"간소화된 채팅 처리 실패: {str(e)}")
        return {
            'message': f"채팅 처리 중 오류가 발생했습니다: {str(e)}",
            'usage': {},
            'metadata': {'error': True}
        }

def build_system_prompt(prompts: List[Dict[str, Any]]) -> str:
    """프롬프트들을 결합하여 시스템 프롬프트 생성"""
    if not prompts:
        return """당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.
기사 제목 생성, 편집 및 관련 질문에 대해 전문적이고 친근하게 답변해주세요."""
    
    system_parts = [
        "당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.",
        "다음 단계별 가이드라인을 참고하여 사용자의 질문에 답변해주세요:"
    ]
    
    # stepOrder가 있는 경우 정렬, 없으면 기본 순서 유지
    if any('stepOrder' in prompt for prompt in prompts):
        sorted_prompts = sorted(prompts, key=lambda x: x.get('stepOrder', 0))
    else:
        sorted_prompts = prompts
    
    for i, prompt in enumerate(sorted_prompts, 1):
        step_order = prompt.get('stepOrder', i)
        category = prompt.get('category', 'Unknown')
        title = prompt.get('title', f"{category.replace('_', ' ').title()} 단계")
        
        # S3에서 프롬프트 텍스트 로드
        prompt_text = load_prompt_text(prompt)
        
        if prompt_text:
            system_parts.append(f"\n=== STEP {step_order}: {title.upper()} ===")
            system_parts.append(prompt_text)
    
    system_parts.append("\n위 가이드라인을 참고하여 사용자의 질문에 전문적이면서도 친근하게 답변해주세요.")
    
    return "\n".join(system_parts)

def load_prompt_text(prompt: Dict[str, Any]) -> str:
    """S3에서 프롬프트 텍스트 로드"""
    try:
        s3_key = prompt.get('s3Key')
        if not s3_key or not PROMPT_BUCKET:
            return ""
        
        response = s3_client.get_object(
            Bucket=PROMPT_BUCKET,
            Key=s3_key
        )
        return response['Body'].read().decode('utf-8')
        
    except Exception as e:
        logger.warning(f"프롬프트 텍스트 로드 실패: {s3_key}, {str(e)}")
        return ""

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트 프롬프트 조회"""
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

def get_recent_chat_history(project_id: str, session_id: str, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """최근 채팅 히스토리 조회"""
    try:
        table = dynamodb.Table(CHAT_HISTORY_TABLE)
        session_key = f"{project_id}#{user_id}#{session_id}"
        
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': session_key},
            ScanIndexForward=False,  # 최신 순으로 정렬
            Limit=limit
        )
        
        messages = response.get('Items', [])
        # 시간 순으로 재정렬 (오래된 것부터)
        messages.reverse()
        return messages
        
    except Exception as e:
        logger.warning(f"채팅 히스토리 조회 실패: {str(e)}")
        return []

def format_chat_history(chat_history: List[Dict[str, Any]]) -> str:
    """채팅 히스토리를 문자열로 포맷팅"""
    if not chat_history:
        return ""
    
    formatted_history = []
    for msg in chat_history[-5:]:  # 최근 5개만 사용
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        if role == 'human':
            formatted_history.append(f"사용자: {content}")
        elif role == 'ai':
            formatted_history.append(f"AI: {content}")
    
    return "\n".join(formatted_history)

def save_chat_message(project_id: str, session_id: str, user_id: str, user_message: str, ai_response: str):
    """채팅 메시지 저장"""
    try:
        table = dynamodb.Table(CHAT_HISTORY_TABLE)
        session_key = f"{project_id}#{user_id}#{session_id}"
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        
        # TTL 설정 (90일 후 자동 삭제)
        ttl = int(datetime.utcnow().timestamp()) + (90 * 24 * 60 * 60)
        
        # 사용자 메시지 저장
        table.put_item(
            Item={
                'pk': session_key,
                'sk': f"TS#{timestamp}#USER",
                'role': 'human',
                'content': user_message,
                'timestamp': timestamp,
                'ttl': ttl
            }
        )
        
        # AI 응답 저장
        table.put_item(
            Item={
                'pk': session_key,
                'sk': f"TS#{timestamp + 1}#AI",
                'role': 'ai',
                'content': ai_response,
                'timestamp': timestamp + 1,
                'ttl': ttl
            }
        )
        
    except Exception as e:
        logger.warning(f"채팅 메시지 저장 실패: {str(e)}")

def get_chat_sessions(event: Dict[str, Any]) -> Dict[str, Any]:
    """채팅 세션 목록 조회"""
    try:
        project_id = event['pathParameters']['projectId']
        
        table = dynamodb.Table(CHAT_SESSION_TABLE)
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id}
        )
        
        sessions = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'projectId': project_id,
                'sessions': sessions
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"채팅 세션 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"세션 목록 조회 실패: {str(e)}")

def get_chat_history(event: Dict[str, Any]) -> Dict[str, Any]:
    """채팅 히스토리 조회"""
    try:
        project_id = event['pathParameters']['projectId']
        session_id = event['pathParameters']['sessionId']
        
        # 전체 히스토리 조회
        chat_history = get_recent_chat_history(project_id, session_id, 'default', limit=100)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'projectId': project_id,
                'sessionId': session_id,
                'messages': chat_history
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"채팅 히스토리 조회 실패: {str(e)}")
        return create_error_response(500, f"히스토리 조회 실패: {str(e)}")

def delete_chat_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """채팅 세션 삭제"""
    try:
        project_id = event['pathParameters']['projectId']
        session_id = event['pathParameters']['sessionId']
        
        # 세션 메타데이터 삭제
        session_table = dynamodb.Table(CHAT_SESSION_TABLE)
        session_table.delete_item(
            Key={
                'projectId': project_id,
                'sessionId': session_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '채팅 세션이 삭제되었습니다',
                'projectId': project_id,
                'sessionId': session_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"채팅 세션 삭제 실패: {str(e)}")
        return create_error_response(500, f"세션 삭제 실패: {str(e)}")

def update_chat_session(project_id: str, session_id: str, user_id: str) -> None:
    """채팅 세션 메타데이터 업데이트"""
    try:
        table = dynamodb.Table(CHAT_SESSION_TABLE)
        table.put_item(
            Item={
                'projectId': project_id,
                'sessionId': session_id,
                'userId': user_id,
                'lastActivity': datetime.utcnow().isoformat(),
                'createdAt': datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.warning(f"세션 메타데이터 업데이트 실패: {str(e)}")

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False, cls=DecimalEncoder)
    }