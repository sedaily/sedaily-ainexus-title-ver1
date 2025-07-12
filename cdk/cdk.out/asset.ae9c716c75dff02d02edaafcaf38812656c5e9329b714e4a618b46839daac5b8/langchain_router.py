import json
import boto3
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time
from decimal import Decimal

# LangChain 임포트
try:
    from langchain_aws import BedrockLLM, BedrockEmbeddings
    from langchain.memory import DynamoDBChatMessageHistory, ConversationSummaryBufferMemory
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain_community.vectorstores import OpenSearchVectorSearch
    from opensearchpy import OpenSearch, RequestsHttpConnection
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    # Lambda Layer가 없는 경우 fallback
    print(f"LangChain 임포트 실패: {e}")
    BedrockLLM = None
    BedrockEmbeddings = None
    DynamoDBChatMessageHistory = None
    ConversationSummaryBufferMemory = None
    LLMChain = None
    PromptTemplate = None
    BaseMessage = None
    HumanMessage = None
    AIMessage = None
    SystemMessage = None
    OpenSearchVectorSearch = None
    OpenSearch = None
    RequestsHttpConnection = None
    LANGCHAIN_AVAILABLE = False

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])

# 환경 변수
CHAT_HISTORY_TABLE = os.environ['CHAT_HISTORY_TABLE']
CHAT_SESSION_TABLE = os.environ['CHAT_SESSION_TABLE']
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
REGION = os.environ['REGION']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']
BEDROCK_SUMMARY_MODEL_ID = os.environ['BEDROCK_SUMMARY_MODEL_ID']

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON 직렬화 가능한 타입으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Decimal을 float 또는 int로 변환
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    LangChain 기반 채팅 라우터 메인 핸들러
    
    Routes:
    - POST /projects/{id}/chat: 채팅 메시지 처리
    - GET /projects/{id}/chat/sessions: 채팅 세션 목록
    - GET /projects/{id}/chat/sessions/{sessionId}: 채팅 히스토리
    - DELETE /projects/{id}/chat/sessions/{sessionId}: 채팅 세션 삭제
    """
    try:
        logger.info(f"채팅 요청 수신: {json.dumps(event, indent=2)}")
        
        # LangChain 의존성 확인
        if not LANGCHAIN_AVAILABLE:
            return create_error_response(503, "LangChain 의존성이 설치되지 않았습니다. 관리자에게 문의하세요.")
        
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        if http_method == 'POST' and '/chat' in path and '/sessions' not in path:
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
    """채팅 메시지 처리"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        user_message = body.get('message', '').strip()
        session_id = body.get('sessionId') or str(uuid.uuid4())
        user_id = body.get('userId', 'default')
        
        if not user_message:
            return create_error_response(400, "메시지가 필요합니다")
        
        # LangChain이 없는 경우 fallback
        if BedrockLLM is None:
            return handle_chat_fallback(project_id, user_message, session_id)
        
        # LangChain 채팅 처리
        response = process_chat_with_langchain(
            project_id, user_id, session_id, user_message
        )
        
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

def process_chat_with_langchain(
    project_id: str, 
    user_id: str, 
    session_id: str, 
    user_message: str
) -> Dict[str, Any]:
    """LangChain을 사용한 채팅 처리"""
    
    # 1. DynamoDBChatMessageHistory 설정
    session_key = f"{project_id}#{user_id}#{session_id}"
    chat_history = DynamoDBChatMessageHistory(
        table_name=CHAT_HISTORY_TABLE,
        session_id=session_key,
        key={
            "pk": session_key,
            "sk": f"TS#{int(time.time() * 1000)}"
        }
    )
    
    # 2. Bedrock LLM 초기화
    llm = BedrockLLM(
        model_id=BEDROCK_MODEL_ID,
        region_name=REGION,
        model_kwargs={
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.9
        }
    )
    
    # 요약용 Titan LLM
    summary_llm = BedrockLLM(
        model_id=BEDROCK_SUMMARY_MODEL_ID,
        region_name=REGION,
        model_kwargs={
            "maxTokenCount": 2000,
            "temperature": 0.3
        }
    )
    
    # 3. ConversationSummaryBufferMemory 설정
    memory = ConversationSummaryBufferMemory(
        llm=summary_llm,
        chat_memory=chat_history,
        max_token_limit=12000,  # Sonnet 안전선
        buffer_window=6,        # 최근 6턴 유지
        return_messages=True
    )
    
    # 4. 프롬프트 조회 및 관련 메시지 RAG
    prompts = get_project_prompts(project_id)
    relevant_messages = get_relevant_messages(session_key, user_message)
    
    # 5. 프롬프트 템플릿 구성
    prompt_template = create_chat_prompt_template(prompts)
    
    # 6. LLMChain 생성 및 실행
    chain = LLMChain(
        llm=llm,
        prompt=prompt_template,
        memory=memory
    )
    
    # 7. 응답 생성
    response = chain.predict(
        input=user_message,
        relevant_context=format_relevant_messages(relevant_messages)
    )
    
    # 8. 세션 메타데이터 업데이트
    update_chat_session(project_id, session_id, user_id)
    
    return {
        'message': response,
        'usage': get_token_usage(user_message, response),
        'metadata': {
            'memory_buffer_size': len(memory.buffer),
            'relevant_messages_count': len(relevant_messages),
            'prompts_loaded': len(prompts)
        }
    }

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트 프롬프트 조회"""
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id}
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        return []

def get_relevant_messages(session_key: str, user_message: str) -> List[Dict[str, Any]]:
    """OpenSearch를 통한 관련 메시지 검색"""
    try:
        # OpenSearch 클라이언트 초기화
        opensearch_client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT.replace('https://', ''), 'port': 443}],
            http_auth=None,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # 임베딩 생성
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v1",
            region_name=REGION
        )
        
        # 벡터 검색
        vectorstore = OpenSearchVectorSearch(
            index_name="chat_messages",
            embedding_function=embeddings,
            opensearch_url=f"https://{OPENSEARCH_ENDPOINT}",
            http_auth=None
        )
        
        # 유사 메시지 검색
        results = vectorstore.similarity_search(
            user_message, 
            k=5,
            filter={"session_key": session_key}
        )
        
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
        
    except Exception as e:
        logger.warning(f"관련 메시지 검색 실패: {str(e)}")
        return []

def create_chat_prompt_template(prompts: List[Dict[str, Any]]):
    """채팅용 프롬프트 템플릿 생성"""
    
    # 프롬프트들을 결합
    combined_prompts = ""
    for prompt in prompts:
        category = prompt.get('category', '')
        # S3에서 실제 프롬프트 텍스트를 로드해야 하지만, 여기서는 간단히 처리
        combined_prompts += f"\n=== {category.upper()} ===\n"
    
    template = f"""당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.

다음은 제목 생성 및 편집 가이드라인입니다:
{combined_prompts}

=== 대화 히스토리 요약 ===
{{history}}

=== 관련 과거 대화 ===
{{relevant_context}}

=== 사용자 질문 ===
{{input}}

위의 모든 가이드라인을 바탕으로 사용자의 질문에 도움이 되는 답변을 제공해주세요.
제목 생성, 편집 조언, 스타일 가이드 등에 대해 전문적이면서도 친근하게 답변해주세요.

답변:"""

    return PromptTemplate(
        input_variables=["history", "relevant_context", "input"],
        template=template
    )

def format_relevant_messages(messages: List[Dict[str, Any]]) -> str:
    """관련 메시지들을 포맷팅"""
    if not messages:
        return "관련된 과거 대화가 없습니다."
    
    formatted = []
    for msg in messages:
        content = msg.get('content', '')
        formatted.append(f"- {content[:200]}...")
    
    return "\n".join(formatted)

def handle_chat_fallback(project_id: str, user_message: str, session_id: str) -> Dict[str, Any]:
    """LangChain이 없는 경우의 fallback 처리"""
    try:
        # 간단한 Bedrock 직접 호출
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": f"제목 생성에 대한 질문입니다: {user_message}"
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        ai_message = response_body['content'][0]['text']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'sessionId': session_id,
                'projectId': project_id,
                'message': ai_message,
                'usage': response_body.get('usage', {}),
                'timestamp': datetime.utcnow().isoformat(),
                'mode': 'fallback'
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"Fallback 처리 실패: {str(e)}")
        return create_error_response(500, f"채팅 처리 실패: {str(e)}")

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
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"채팅 세션 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"세션 목록 조회 실패: {str(e)}")

def get_chat_history(event: Dict[str, Any]) -> Dict[str, Any]:
    """채팅 히스토리 조회"""
    try:
        project_id = event['pathParameters']['projectId']
        session_id = event['pathParameters']['sessionId']
        
        # DynamoDB에서 채팅 히스토리 조회
        table = dynamodb.Table(CHAT_HISTORY_TABLE)
        session_key = f"{project_id}#default#{session_id}"
        
        response = table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': session_key},
            ScanIndexForward=True  # 시간 순 정렬
        )
        
        messages = response.get('Items', [])
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'projectId': project_id,
                'sessionId': session_id,
                'messages': messages
            }, ensure_ascii=False)
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
        
        # 채팅 히스토리 삭제는 TTL로 자동 처리
        
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

def get_token_usage(user_message: str, ai_response: str) -> Dict[str, Any]:
    """토큰 사용량 추정"""
    # 간단한 토큰 추정 (실제로는 Bedrock 응답에서 가져와야 함)
    input_tokens = len(user_message.split()) * 1.3
    output_tokens = len(ai_response.split()) * 1.3
    
    return {
        'input_tokens': int(input_tokens),
        'output_tokens': int(output_tokens),
        'total_tokens': int(input_tokens + output_tokens)
    }

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