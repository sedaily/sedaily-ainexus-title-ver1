import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=os.environ['REGION'])

# 환경 변수
PROJECT_TABLE = os.environ['PROJECT_TABLE']
CHAT_SESSION_TABLE = os.environ['CHAT_SESSION_TABLE']
BEDROCK_AGENT_ID = os.environ['BEDROCK_AGENT_ID']
BEDROCK_AGENT_ALIAS_ID = os.environ['BEDROCK_AGENT_ALIAS_ID']
REGION = os.environ['REGION']

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
    Bedrock Agent 기반 채팅 라우터 메인 핸들러
    
    Routes:
    - POST /projects/{id}/agent-chat: Bedrock Agent를 통한 채팅 메시지 처리
    - GET /projects/{id}/agent-chat/sessions: 채팅 세션 목록
    - GET /projects/{id}/agent-chat/sessions/{sessionId}: 채팅 히스토리
    - DELETE /projects/{id}/agent-chat/sessions/{sessionId}: 채팅 세션 삭제
    """
    try:
        logger.info(f"Bedrock Agent 채팅 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        if http_method == 'POST' and '/agent-chat' in path and '/sessions' not in path:
            return handle_agent_chat_message(event)
        elif http_method == 'GET' and '/sessions' in path:
            if event.get('pathParameters', {}).get('sessionId'):
                return get_agent_chat_history(event)
            else:
                return get_agent_chat_sessions(event)
        elif http_method == 'DELETE' and '/sessions' in path:
            return delete_agent_chat_session(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"Bedrock Agent 채팅 요청 처리 중 오류 발생: {str(e)}")
        return create_error_response(500, f"내부 서버 오류: {str(e)}")

def handle_agent_chat_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """Bedrock Agent를 통한 채팅 메시지 처리"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        user_message = body.get('message', '').strip()
        session_id = body.get('sessionId') or str(uuid.uuid4())
        user_id = body.get('userId', 'default')
        
        if not user_message:
            return create_error_response(400, "메시지가 필요합니다")
        
        # 프로젝트 정보 조회 (AI 커스터마이징 필드 포함)
        project_info = get_project_info(project_id)
        if not project_info:
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        # 동적 프롬프트 생성
        enhanced_message = create_dynamic_prompt(user_message, project_info)
        
        # Bedrock Agent 호출
        response = invoke_bedrock_agent(
            agent_id=BEDROCK_AGENT_ID,
            agent_alias_id=BEDROCK_AGENT_ALIAS_ID,
            session_id=session_id,
            input_text=enhanced_message
        )
        
        # 세션 메타데이터 업데이트
        update_agent_chat_session(project_id, session_id, user_id)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'sessionId': session_id,
                'projectId': project_id,
                'message': response['output']['text'],
                'agentResponse': response,
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {
                    'project_customization': {
                        'aiRole': project_info.get('aiRole', ''),
                        'targetAudience': project_info.get('targetAudience', ''),
                        'outputFormat': project_info.get('outputFormat', '')
                    }
                }
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Bedrock Agent 채팅 메시지 처리 실패: {str(e)}")
        return create_error_response(500, f"채팅 처리 실패: {str(e)}")

def get_project_info(project_id: str) -> Optional[Dict[str, Any]]:
    """프로젝트 정보 및 AI 커스터마이징 필드 조회"""
    try:
        table = dynamodb.Table(PROJECT_TABLE)
        response = table.get_item(Key={'projectId': project_id})
        
        if 'Item' not in response:
            return None
            
        return response['Item']
        
    except Exception as e:
        logger.error(f"프로젝트 정보 조회 실패: {str(e)}")
        return None

def create_dynamic_prompt(user_message: str, project_info: Dict[str, Any]) -> str:
    """프로젝트별 AI 커스터마이징 정보를 바탕으로 동적 프롬프트 생성"""
    
    # 프로젝트 커스터마이징 정보 추출
    ai_role = project_info.get('aiRole', '')
    ai_instructions = project_info.get('aiInstructions', '')
    target_audience = project_info.get('targetAudience', '일반독자')
    output_format = project_info.get('outputFormat', 'multiple')
    style_guidelines = project_info.get('styleGuidelines', '')
    
    # 동적 프롬프트 구성
    dynamic_context = f"""
=== 프로젝트별 AI 어시스턴트 설정 ===
프로젝트: {project_info.get('name', 'Unknown Project')}

AI 역할: {ai_role if ai_role else '제목 생성 전문가'}

타겟 독자층: {target_audience}
- 일반독자: 쉽고 이해하기 쉬운 표현 사용
- 전문가: 업계 전문 용어와 깊이 있는 분석 포함
- 투자자: 투자 관점과 수익성에 초점
- 경영진: 비즈니스 전략과 의사결정에 도움되는 관점

출력 형식: {output_format}
- single: 가장 적합한 제목 1개만 제안
- multiple: 3-5개의 다양한 스타일 제목 제안
- detailed: 제목과 함께 선택 이유 및 개선 방향 설명

추가 지침:
{ai_instructions if ai_instructions else '표준 제목 생성 가이드라인을 따르세요.'}

스타일 가이드라인:
{style_guidelines if style_guidelines else '서울경제신문의 기본 스타일을 유지하세요.'}

=== 사용자 요청 ===
{user_message}

위의 프로젝트별 설정을 반영하여 사용자의 요청에 답변해주세요."""
    
    return dynamic_context

def invoke_bedrock_agent(
    agent_id: str, 
    agent_alias_id: str, 
    session_id: str, 
    input_text: str
) -> Dict[str, Any]:
    """Bedrock Agent 호출"""
    try:
        response = bedrock_agent.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=input_text
        )
        
        # 스트리밍 응답 처리
        output_text = ""
        for event in response['completion']:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    output_text += chunk['bytes'].decode('utf-8')
        
        return {
            'output': {
                'text': output_text
            },
            'sessionId': session_id,
            'responseMetadata': response.get('ResponseMetadata', {})
        }
        
    except Exception as e:
        logger.error(f"Bedrock Agent 호출 실패: {str(e)}")
        raise

def get_agent_chat_sessions(event: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 채팅 세션 목록 조회"""
    try:
        project_id = event['pathParameters']['projectId']
        
        table = dynamodb.Table(CHAT_SESSION_TABLE)
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id},
            FilterExpression='attribute_exists(agentSession)'  # Agent 세션만 필터링
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
        logger.error(f"Agent 채팅 세션 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"세션 목록 조회 실패: {str(e)}")

def get_agent_chat_history(event: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 채팅 히스토리 조회"""
    try:
        project_id = event['pathParameters']['projectId']
        session_id = event['pathParameters']['sessionId']
        
        # 실제 구현에서는 Bedrock Agent의 세션 히스토리를 조회
        # 현재는 간단한 응답만 반환
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'projectId': project_id,
                'sessionId': session_id,
                'messages': [],  # Bedrock Agent 세션에서 히스토리 조회 필요
                'note': 'Bedrock Agent 세션 히스토리는 Agent 내부에서 관리됩니다'
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Agent 채팅 히스토리 조회 실패: {str(e)}")
        return create_error_response(500, f"히스토리 조회 실패: {str(e)}")

def delete_agent_chat_session(event: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 채팅 세션 삭제"""
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
                'message': 'Agent 채팅 세션이 삭제되었습니다',
                'projectId': project_id,
                'sessionId': session_id
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"Agent 채팅 세션 삭제 실패: {str(e)}")
        return create_error_response(500, f"세션 삭제 실패: {str(e)}")

def update_agent_chat_session(project_id: str, session_id: str, user_id: str) -> None:
    """Agent 채팅 세션 메타데이터 업데이트"""
    try:
        table = dynamodb.Table(CHAT_SESSION_TABLE)
        table.put_item(
            Item={
                'projectId': project_id,
                'sessionId': session_id,
                'userId': user_id,
                'lastActivity': datetime.utcnow().isoformat(),
                'createdAt': datetime.utcnow().isoformat(),
                'agentSession': True,  # Agent 세션 구분자
                'agentId': BEDROCK_AGENT_ID,
                'agentAliasId': BEDROCK_AGENT_ALIAS_ID
            }
        )
    except Exception as e:
        logger.warning(f"Agent 세션 메타데이터 업데이트 실패: {str(e)}")

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
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
        }, ensure_ascii=False, cls=DecimalEncoder)
    }