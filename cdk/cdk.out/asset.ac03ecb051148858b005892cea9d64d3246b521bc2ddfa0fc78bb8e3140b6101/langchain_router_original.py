import json
import boto3
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# LangChain 임포트
try:
    from langchain_aws import ChatBedrock, BedrockEmbeddings
    from langchain.memory import DynamoDBChatMessageHistory, ConversationSummaryBufferMemory
    from langchain.chains import LLMChain, SequentialChain
    from langchain.prompts import PromptTemplate
    from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain.agents import Tool, AgentExecutor, create_react_agent
    from langchain.tools import BaseTool
    from langchain import hub
    LANGCHAIN_AVAILABLE = True
    logger.info("LangChain 의존성 로드 성공")
except ImportError as e:
    logger.error(f"LangChain 임포트 실패: {e}")
    ChatBedrock = None
    BedrockEmbeddings = None
    DynamoDBChatMessageHistory = None
    ConversationSummaryBufferMemory = None
    LLMChain = None
    SequentialChain = None
    PromptTemplate = None
    BaseMessage = None
    HumanMessage = None
    AIMessage = None
    SystemMessage = None
    Tool = None
    AgentExecutor = None
    create_react_agent = None
    BaseTool = None
    hub = None
    LANGCHAIN_AVAILABLE = False

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
            # Decimal을 float 또는 int로 변환
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

class TitleGenerationTool(BaseTool):
    """제목 생성 전용 도구"""
    name = "title_generator"
    description = "기사 원문을 받아서 제목을 생성하는 도구입니다."
    
    def _run(self, article_text: str) -> str:
        """기사 원문으로부터 제목 생성"""
        try:
            # 직접 Bedrock 호출
            response = bedrock_runtime.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.7,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"다음 기사의 제목을 생성해주세요:\n\n{article_text}"
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"제목 생성 실패: {str(e)}")
            return f"제목 생성 중 오류가 발생했습니다: {str(e)}"

class StyleValidationTool(BaseTool):
    """스타일 가이드 검증 도구"""
    name = "style_validator"
    description = "생성된 제목이 스타일 가이드를 준수하는지 검증하는 도구입니다."
    
    def _run(self, title: str, style_guide: str = "") -> str:
        """제목의 스타일 가이드 준수 여부 검증"""
        try:
            prompt = f"""
다음 제목이 스타일 가이드를 준수하는지 검증해주세요:

제목: {title}

스타일 가이드:
{style_guide if style_guide else "서울경제신문의 기본 스타일 가이드를 적용"}

검증 결과를 JSON 형태로 반환해주세요:
{{
  "valid": true/false,
  "issues": ["문제점1", "문제점2"],
  "suggestions": ["개선안1", "개선안2"]
}}
"""
            
            response = bedrock_runtime.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "temperature": 0.3,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"스타일 검증 실패: {str(e)}")
            return f"스타일 검증 중 오류가 발생했습니다: {str(e)}"

class VectorSearchTool(BaseTool):
    """벡터 검색 도구"""
    name = "vector_search"
    description = "사용자의 질문과 관련된 프롬프트를 검색하는 도구입니다."
    
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.embedding_processor = EmbeddingProcessor()
    
    def _run(self, query: str) -> str:
        """질문과 관련된 프롬프트 검색"""
        try:
            # 질문을 임베딩으로 변환
            query_embedding = self.embedding_processor.generate_embedding(query)
            
            if not query_embedding:
                return "검색 중 오류가 발생했습니다."
            
            # 프로젝트의 모든 임베딩 조회
            embeddings = self._get_project_embeddings()
            
            if not embeddings:
                return "관련 프롬프트를 찾을 수 없습니다."
            
            # 코사인 유사도 계산
            similarities = []
            for embedding_data in embeddings:
                similarity = self._calculate_cosine_similarity(
                    query_embedding, 
                    embedding_data['embedding']
                )
                similarities.append({
                    'similarity': similarity,
                    'promptId': embedding_data['promptId'],
                    'metadata': embedding_data['metadata']
                })
            
            # 유사도 순으로 정렬
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 상위 3개 결과 반환
            top_results = similarities[:3]
            
            result_text = "관련 프롬프트들:\n"
            for i, result in enumerate(top_results, 1):
                metadata = result['metadata']
                result_text += f"{i}. {metadata.get('title', 'Unknown')} (유사도: {result['similarity']:.3f})\n"
                result_text += f"   카테고리: {metadata.get('category', 'Unknown')}\n"
                result_text += f"   단계: {metadata.get('stepOrder', 'Unknown')}\n\n"
            
            return result_text
            
        except Exception as e:
            logger.error(f"벡터 검색 실패: {str(e)}")
            return f"검색 중 오류가 발생했습니다: {str(e)}"
    
    def _get_project_embeddings(self) -> List[Dict[str, Any]]:
        """프로젝트의 모든 임베딩 조회"""
        try:
            # S3에서 임베딩 파일들 조회
            response = s3_client.list_objects_v2(
                Bucket=PROMPT_BUCKET,
                Prefix=f"embeddings/{self.project_id}/"
            )
            
            embeddings = []
            for obj in response.get('Contents', []):
                try:
                    embedding_response = s3_client.get_object(
                        Bucket=PROMPT_BUCKET,
                        Key=obj['Key']
                    )
                    embedding_data = json.loads(embedding_response['Body'].read().decode('utf-8'))
                    embeddings.append(embedding_data)
                except Exception as e:
                    logger.warning(f"임베딩 파일 로드 실패: {obj['Key']}, {str(e)}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"임베딩 조회 실패: {str(e)}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            import math
            
            # 벡터 길이가 다른 경우 처리
            if len(vec1) != len(vec2):
                return 0.0
            
            # 내적 계산
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # 벡터 크기 계산
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            # 0으로 나누기 방지
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            # 코사인 유사도 계산
            similarity = dot_product / (magnitude1 * magnitude2)
            return similarity
            
        except Exception as e:
            logger.error(f"코사인 유사도 계산 실패: {str(e)}")
            return 0.0

class EmbeddingProcessor:
    """임베딩 처리 클래스"""
    
    def __init__(self):
        self.model_id = "amazon.titan-embed-text-v1"
        self.bedrock_client = bedrock_runtime
    
    def generate_embedding(self, text: str) -> List[float]:
        """텍스트에 대한 임베딩 벡터 생성"""
        try:
            # 텍스트 전처리
            cleaned_text = self._preprocess_text(text)
            
            # Bedrock Titan Embeddings 호출
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputText": cleaned_text
                })
            )
            
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            logger.info(f"임베딩 생성 성공: {len(embedding)} 차원")
            return embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            return []
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        # 기본적인 정리
        cleaned = text.strip()
        
        # 너무 긴 텍스트는 잘라내기 (Titan 임베딩 제한: 8192 토큰)
        if len(cleaned) > 8000:
            cleaned = cleaned[:8000] + "..."
        
        return cleaned

class PromptChainOrchestrator:
    """프롬프트 체이닝 오케스트레이터"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.llm = None
        self.chains = []
        self.tools = []
        
        if LANGCHAIN_AVAILABLE:
            self.llm = ChatBedrock(
                model_id=BEDROCK_MODEL_ID,
                region_name=REGION,
                model_kwargs={
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            )
            
            # 도구 초기화
            self.tools = [
                TitleGenerationTool(),
                StyleValidationTool(),
                VectorSearchTool(project_id)
            ]
    
    def build_prompt_chain(self, prompts: List[Dict[str, Any]]) -> Optional[SequentialChain]:
        """프롬프트 카드들을 순차적 체인으로 구성"""
        if not LANGCHAIN_AVAILABLE or not prompts:
            return None
        
        try:
            chains = []
            
            # 각 프롬프트 카드를 개별 체인으로 변환
            for i, prompt_card in enumerate(prompts):
                step_order = prompt_card.get('stepOrder', i + 1)
                category = prompt_card.get('category', 'unknown')
                
                # S3에서 프롬프트 텍스트 로드
                prompt_text = self._load_prompt_text(prompt_card)
                
                if not prompt_text:
                    continue
                
                # 체인별 입력/출력 변수 정의
                input_key = f"step_{step_order}_input" if i > 0 else "input"
                output_key = f"step_{step_order}_output"
                
                # 프롬프트 템플릿 생성
                template = f"""
=== STEP {step_order}: {category.upper()} ===

{prompt_text}

이전 단계 결과: {{{input_key}}}

위의 지침에 따라 다음 단계를 수행해주세요:
"""
                
                prompt_template = PromptTemplate(
                    input_variables=[input_key],
                    output_key=output_key,
                    template=template
                )
                
                # LLM 체인 생성
                chain = LLMChain(
                    llm=self.llm,
                    prompt=prompt_template,
                    output_key=output_key
                )
                
                chains.append(chain)
            
            if not chains:
                return None
            
            # 순차적 체인 생성
            input_variables = ["input"]
            output_variables = [chain.output_key for chain in chains]
            
            sequential_chain = SequentialChain(
                chains=chains,
                input_variables=input_variables,
                output_variables=output_variables,
                verbose=True
            )
            
            logger.info(f"프롬프트 체인 구성 완료: {len(chains)}개 단계")
            return sequential_chain
            
        except Exception as e:
            logger.error(f"프롬프트 체인 구성 실패: {str(e)}")
            return None
    
    def create_agent_executor(self, prompts: List[Dict[str, Any]]) -> Optional[AgentExecutor]:
        """에이전트 실행기 생성"""
        if not LANGCHAIN_AVAILABLE or not prompts:
            return None
        
        try:
            # 프롬프트 기반 시스템 메시지 생성
            system_message = self._build_system_message(prompts)
            
            # ReAct 에이전트 생성
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=hub.pull("hwchase17/react") if hub else None
            )
            
            # 에이전트 실행기 생성
            agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5
            )
            
            logger.info(f"에이전트 실행기 생성 완료: {len(self.tools)}개 도구")
            return agent_executor
            
        except Exception as e:
            logger.error(f"에이전트 실행기 생성 실패: {str(e)}")
            return None
    
    def build_smart_prompt_chain(self, user_message: str) -> Optional[SequentialChain]:
        """사용자 메시지를 기반으로 스마트한 프롬프트 체인 구성"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        try:
            # 벡터 검색으로 관련 프롬프트 찾기
            vector_search_tool = VectorSearchTool(self.project_id)
            search_results = vector_search_tool._run(user_message)
            
            # 검색 결과를 기반으로 관련 프롬프트 ID 추출
            relevant_prompt_ids = self._extract_prompt_ids_from_search(search_results)
            
            # 관련 프롬프트들만 조회
            relevant_prompts = self._get_relevant_prompts(relevant_prompt_ids)
            
            if not relevant_prompts:
                # 관련 프롬프트가 없으면 전체 프롬프트 사용
                relevant_prompts = get_project_prompts(self.project_id)
            
            # 프롬프트 체인 구성
            return self.build_prompt_chain(relevant_prompts)
            
        except Exception as e:
            logger.error(f"스마트 프롬프트 체인 구성 실패: {str(e)}")
            return None
    
    def _extract_prompt_ids_from_search(self, search_results: str) -> List[str]:
        """검색 결과에서 프롬프트 ID 추출"""
        # 실제 구현에서는 VectorSearchTool의 결과를 파싱
        # 현재는 간단한 구현으로 처리
        prompt_ids = []
        
        try:
            # 검색 결과에서 프롬프트 ID 패턴 찾기
            import re
            # 간단한 패턴 매칭 (실제로는 더 정교하게 구현)
            lines = search_results.split('\n')
            for line in lines:
                if 'promptId' in line:
                    # JSON이나 특정 패턴에서 ID 추출
                    match = re.search(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', line)
                    if match:
                        prompt_ids.append(match.group())
        
        except Exception as e:
            logger.warning(f"프롬프트 ID 추출 실패: {str(e)}")
        
        return prompt_ids[:3]  # 상위 3개만 사용
    
    def _get_relevant_prompts(self, prompt_ids: List[str]) -> List[Dict[str, Any]]:
        """관련 프롬프트들만 조회"""
        if not prompt_ids:
            return []
        
        try:
            table = dynamodb.Table(PROMPT_META_TABLE)
            relevant_prompts = []
            
            for prompt_id in prompt_ids:
                response = table.get_item(
                    Key={'projectId': self.project_id, 'promptId': prompt_id}
                )
                
                if 'Item' in response:
                    relevant_prompts.append(response['Item'])
            
            # stepOrder 순으로 정렬
            relevant_prompts.sort(key=lambda x: x.get('stepOrder', 0))
            return relevant_prompts
            
        except Exception as e:
            logger.error(f"관련 프롬프트 조회 실패: {str(e)}")
            return []
    
    def _load_prompt_text(self, prompt_card: Dict[str, Any]) -> str:
        """S3에서 프롬프트 텍스트 로드"""
        try:
            s3_key = prompt_card.get('s3Key')
            if not s3_key:
                return ""
            
            response = s3_client.get_object(
                Bucket=PROMPT_BUCKET,
                Key=s3_key
            )
            return response['Body'].read().decode('utf-8')
            
        except Exception as e:
            logger.warning(f"프롬프트 텍스트 로드 실패: {s3_key}, {str(e)}")
            return ""
    
    def _build_system_message(self, prompts: List[Dict[str, Any]]) -> str:
        """프롬프트들을 기반으로 시스템 메시지 구성"""
        system_parts = [
            "당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.",
            "다음 단계별 가이드라인을 순서대로 따라 작업을 수행해주세요:"
        ]
        
        for prompt_card in prompts:
            step_order = prompt_card.get('stepOrder', 1)
            category = prompt_card.get('category', 'unknown')
            title = prompt_card.get('title', f"Step {step_order}")
            
            prompt_text = self._load_prompt_text(prompt_card)
            if prompt_text:
                system_parts.append(f"\n=== STEP {step_order}: {title.upper()} ===")
                system_parts.append(prompt_text)
        
        return "\n".join(system_parts)

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
        if ChatBedrock is None:
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
    """LangChain을 사용한 고급 채팅 처리 (프롬프트 체이닝 포함)"""
    
    # 1. 프롬프트 체이닝 오케스트레이터 초기화
    orchestrator = PromptChainOrchestrator(project_id)
    
    # 2. 프로젝트 프롬프트 조회
    prompts = get_project_prompts(project_id)
    
    # 3. 채팅 메모리 설정
    session_key = f"{project_id}#{user_id}#{session_id}"
    chat_history = DynamoDBChatMessageHistory(
        table_name=CHAT_HISTORY_TABLE,
        session_id=session_key,
        key={
            "pk": session_key,
            "sk": f"TS#{int(time.time() * 1000)}"
        }
    )
    
    # 4. LLM 및 메모리 초기화
    llm = ChatBedrock(
        model_id=BEDROCK_MODEL_ID,
        region_name=REGION,
        model_kwargs={
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.9
        }
    )
    
    summary_llm = ChatBedrock(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region_name=REGION,
        model_kwargs={
            "max_tokens": 2000,
            "temperature": 0.3
        }
    )
    
    memory = ConversationSummaryBufferMemory(
        llm=summary_llm,
        chat_memory=chat_history,
        max_token_limit=12000,
        buffer_window=6,
        return_messages=True
    )
    
    # 5. 프롬프트 체이닝 또는 에이전트 실행
    response_text = ""
    processing_mode = "simple"
    
    if "제목 생성" in user_message or "title" in user_message.lower():
        # 제목 생성 요청 시 스마트 프롬프트 체이닝 사용
        sequential_chain = orchestrator.build_smart_prompt_chain(user_message)
        
        if sequential_chain:
            try:
                result = sequential_chain.run(input=user_message)
                response_text = result
                processing_mode = "smart_chain"
            except Exception as e:
                logger.error(f"스마트 프롬프트 체이닝 실행 실패: {str(e)}")
                response_text = f"스마트 프롬프트 체이닝 처리 중 오류가 발생했습니다: {str(e)}"
        
        # 스마트 체이닝 실패 시 기본 체이닝 시도
        if not response_text or "오류" in response_text:
            sequential_chain = orchestrator.build_prompt_chain(prompts)
            
            if sequential_chain:
                try:
                    result = sequential_chain.run(input=user_message)
                    response_text = result
                    processing_mode = "basic_chain"
                except Exception as e:
                    logger.error(f"기본 프롬프트 체이닝 실행 실패: {str(e)}")
                    response_text = f"기본 프롬프트 체이닝 처리 중 오류가 발생했습니다: {str(e)}"
        
        # 체이닝 모두 실패 시 에이전트 실행
        if not response_text or "오류" in response_text:
            agent_executor = orchestrator.create_agent_executor(prompts)
            
            if agent_executor:
                try:
                    result = agent_executor.run(user_message)
                    response_text = result
                    processing_mode = "agent"
                except Exception as e:
                    logger.error(f"에이전트 실행 실패: {str(e)}")
                    response_text = f"에이전트 처리 중 오류가 발생했습니다: {str(e)}"
    
    # 6. 일반 채팅 처리 (프롬프트 체이닝 미사용)
    if not response_text:
        prompt_template = create_chat_prompt_template(prompts)
        
        if prompt_template:
            chain = LLMChain(
                llm=llm,
                prompt=prompt_template,
                memory=memory
            )
            
            try:
                response_text = chain.predict(
                    input=user_message,
                    relevant_context=""
                )
                processing_mode = "simple"
            except Exception as e:
                logger.error(f"일반 채팅 처리 실패: {str(e)}")
                response_text = f"채팅 처리 중 오류가 발생했습니다: {str(e)}"
    
    # 7. 세션 메타데이터 업데이트
    update_chat_session(project_id, session_id, user_id)
    
    return {
        'message': response_text,
        'usage': get_token_usage(user_message, response_text),
        'metadata': {
            'processing_mode': processing_mode,
            'prompts_loaded': len(prompts),
            'memory_buffer_size': len(memory.buffer) if memory else 0
        }
    }

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트 프롬프트 조회 (카드 시스템 우선, 레거시 호환)"""
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # 새로운 프롬프트 카드 시스템: GSI를 사용하여 stepOrder 순으로 조회
        try:
            response = table.query(
                IndexName='projectId-stepOrder-index',
                KeyConditionExpression='projectId = :projectId',
                FilterExpression='enabled = :enabled',  # 활성화된 카드만
                ExpressionAttributeValues={
                    ':projectId': project_id,
                    ':enabled': True
                },
                ScanIndexForward=True  # stepOrder 오름차순 정렬
            )
            
            prompt_cards = response.get('Items', [])
            if prompt_cards:
                logger.info(f"프롬프트 카드 {len(prompt_cards)}개 로드됨")
                return prompt_cards
                
        except Exception as gsi_error:
            logger.warning(f"GSI 조회 실패, 레거시 모드로 전환: {str(gsi_error)}")
        
        # 레거시 시스템: 기존 방식으로 조회
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id}
        )
        
        legacy_prompts = response.get('Items', [])
        logger.info(f"레거시 프롬프트 {len(legacy_prompts)}개 로드됨")
        return legacy_prompts
        
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
    """채팅용 프롬프트 템플릿 생성 (카드 시스템 지원)"""
    
    # LangChain이 사용 불가능한 경우 None 반환
    if not LANGCHAIN_AVAILABLE or PromptTemplate is None:
        return None
    
    # 프롬프트들을 step_order 순으로 결합
    combined_prompts = ""
    
    if not prompts:
        combined_prompts = "현재 활성화된 프롬프트 가이드라인이 없습니다."
    else:
        # stepOrder가 있는 경우 (새로운 카드 시스템)
        if any('stepOrder' in prompt for prompt in prompts):
            # 이미 정렬되어 온 것이므로 그대로 사용
            sorted_prompts = prompts
        else:
            # 레거시 시스템의 경우 category로 정렬
            sorted_prompts = sorted(prompts, key=lambda x: x.get('category', ''))
        
        for i, prompt in enumerate(sorted_prompts, 1):
            category = prompt.get('category', 'Unknown')
            step_order = prompt.get('stepOrder', i)
            title = prompt.get('title', f"{category.replace('_', ' ').title()} 단계")
            
            # S3에서 프롬프트 텍스트 로드 시도
            prompt_text = ""
            if PROMPT_BUCKET and prompt.get('s3Key'):
                try:
                    s3_response = s3_client.get_object(
                        Bucket=PROMPT_BUCKET,
                        Key=prompt['s3Key']
                    )
                    prompt_text = s3_response['Body'].read().decode('utf-8')
                except Exception as e:
                    logger.warning(f"S3에서 프롬프트 로드 실패: {prompt.get('s3Key')}, {str(e)}")
                    prompt_text = f"[프롬프트 로드 실패: {category}]"
            
            # 프롬프트 텍스트가 있는 경우만 포함
            if prompt_text:
                combined_prompts += f"\n=== STEP {step_order}: {title.upper()} ===\n"
                combined_prompts += f"{prompt_text}\n"
    
    template = f"""당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.

다음은 단계별 제목 생성 및 편집 가이드라인입니다:
{combined_prompts}

=== 대화 히스토리 요약 ===
{{history}}

=== 관련 과거 대화 ===
{{relevant_context}}

=== 사용자 질문 ===
{{input}}

위의 모든 가이드라인을 step 순서대로 참고하여 사용자의 질문에 도움이 되는 답변을 제공해주세요.
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