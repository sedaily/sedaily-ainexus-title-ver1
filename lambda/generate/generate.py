"""
AI 대화 생성 Lambda 함수 (LangChain 적용 버전)
- Runnable과 Memory를 사용하여 대화 기억 기능 구현
- 확장성과 유지보수성이 높은 구조
- CORS 오류 수정 및 간소화
"""
import json
import os
import traceback
import boto3
from datetime import datetime

# --- AWS 클라이언트 및 기본 설정 ---
bedrock_client = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "YOUR-REGION"))
dynamodb_client = boto3.client("dynamodb", region_name=os.environ.get("REGION", "YOUR-REGION"))
PROMPT_META_TABLE = os.environ.get("PROMPT_META_TABLE", "BedrockDiyPrompts")
# 기본 모델 ID (프론트엔드에서 지정하지 않을 때 사용)
DEFAULT_MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

# 토큰 및 길이 제한 설정
MAX_INPUT_LENGTH = 150000  # 약 150K 문자 (약 37.5K 토큰)
MAX_TOTAL_TOKENS = 180000  # Claude의 200K 토큰 한계 고려
CHUNK_SIZE = 50000  # 청킹 시 사용할 크기

# 지원되는 모델 목록
SUPPORTED_MODELS = {
    # Anthropic Claude 모델들
    "anthropic.claude-opus-4-v1:0": {"name": "Claude Opus 4", "provider": "Anthropic"},
    "anthropic.claude-sonnet-4-v1:0": {"name": "Claude Sonnet 4", "provider": "Anthropic"},
    "anthropic.claude-3-7-sonnet-v1:0": {"name": "Claude 3.7 Sonnet", "provider": "Anthropic"},
    "anthropic.claude-3-5-haiku-20241022-v1:0": {"name": "Claude 3.5 Haiku", "provider": "Anthropic"},
    "apac.anthropic.claude-sonnet-4-20250514-v1:0": {"name": "Claude 3.5 Sonnet v2", "provider": "Anthropic"},
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {"name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
    "anthropic.claude-3-opus-20240229-v1:0": {"name": "Claude 3 Opus", "provider": "Anthropic"},
    "anthropic.claude-3-haiku-20240307-v1:0": {"name": "Claude 3 Haiku", "provider": "Anthropic"},
    "apac.anthropic.claude-sonnet-4-20250514-v1:0": {"name": "Claude 3 Sonnet", "provider": "Anthropic"},
    
    # Meta Llama 모델들
    "meta.llama4-scout-17b-instruct-v4:0": {"name": "Llama 4 Scout 17B", "provider": "Meta"},
    "meta.llama4-maverick-17b-instruct-v4:0": {"name": "Llama 4 Maverick 17B", "provider": "Meta"},
    "meta.llama3-3-70b-instruct-v1:0": {"name": "Llama 3.3 70B", "provider": "Meta"},
    "meta.llama3-2-11b-instruct-v1:0": {"name": "Llama 3.2 11B Vision", "provider": "Meta"},
    "meta.llama3-2-1b-instruct-v1:0": {"name": "Llama 3.2 1B", "provider": "Meta"},
    "meta.llama3-2-3b-instruct-v1:0": {"name": "Llama 3.2 3B", "provider": "Meta"},
    
    # Amazon Nova 모델들
    "amazon.nova-premier-v1:0": {"name": "Nova Premier", "provider": "Amazon"},
    "amazon.nova-lite-v1:0": {"name": "Nova Lite", "provider": "Amazon"},
    "amazon.nova-micro-v1:0": {"name": "Nova Micro", "provider": "Amazon"},
    "amazon.nova-pro-v1:0": {"name": "Nova Pro", "provider": "Amazon"},
}

def handler(event, context):
    """
    API Gateway 요청을 처리하여 Bedrock 스트리밍 응답을 반환합니다.
    - GET 요청은 EventSource (SSE)를 위해 사용됩니다 (긴 URL 문제로 현재는 비권장).
    - POST 요청이 기본 스트리밍 방식입니다.
    """
    try:
        print(f"이벤트 수신: {json.dumps(event)}")
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        
        # S3 presigned URL을 통한 대용량 파일 처리
        if path == "/generate/s3-upload":
            return _handle_s3_upload_request(event)
        elif path == "/generate/s3-process":
            return _handle_s3_process_request(event)

        # 요청 본문(body) 파싱
        if http_method == 'GET':
            params = event.get('queryStringParameters') or {}
            user_input = params.get('userInput', '')
            chat_history_str = params.get('chat_history', '[]')
            chat_history = json.loads(chat_history_str)
            model_id = params.get('modelId', DEFAULT_MODEL_ID)
        else: # POST
            body = json.loads(event.get('body', '{}'))
            user_input = body.get('userInput', '')
            chat_history = body.get('chat_history', [])
            prompt_cards = body.get('prompt_cards', [])
            model_id = body.get('modelId', DEFAULT_MODEL_ID)
            
        if not user_input.strip():
            return _create_error_response(400, "사용자 입력이 필요합니다.")
        
        # 입력 길이 체크 및 전처리
        content_length = len(user_input)
        
        # 대용량 문서 감지 (200K 문자 이상)
        if content_length > 200000:
            print(f"대용량 문서 감지: {content_length:,}자 - 배치 처리 모드")
            return _handle_batch_processing(user_input, chat_history, prompt_cards, model_id)
        
        processed_input = _preprocess_long_content(user_input)
        if isinstance(processed_input, dict) and processed_input.get('error'):
            return _create_error_response(400, processed_input['error'])
        
        # 전처리된 입력으로 교체
        user_input = processed_input
        
        # 모델 ID 검증
        if model_id not in SUPPORTED_MODELS:
            print(f"지원되지 않는 모델 ID: {model_id}")
            model_id = DEFAULT_MODEL_ID
        
        # GET 요청일 때 prompt_cards 처리
        if http_method == 'GET':
            prompt_cards = []
        
        print(f"선택된 모델: {model_id} ({SUPPORTED_MODELS.get(model_id, {}).get('name', 'Unknown')})")
        print(f"요청 본문에서 받은 modelId: {body.get('modelId') if http_method == 'POST' else params.get('modelId')}")
        
        # 스트리밍 또는 일반 생성 분기
        if "/stream" in path:
            return _handle_streaming_generation(user_input, chat_history, prompt_cards, model_id)
        else:
            return _handle_standard_generation(user_input, chat_history, prompt_cards, model_id)

    except json.JSONDecodeError:
        print("JSON 파싱 오류 발생")
        return _create_error_response(400, "잘못된 JSON 형식입니다.")
    except Exception as e:
        print(f"오류 발생: {traceback.format_exc()}")
        return _create_error_response(500, f"서버 내부 오류: {e}")

def _handle_streaming_generation(user_input, chat_history, prompt_cards, model_id):
    """
    Bedrock에서 스트리밍 응답을 받아 실시간으로 반환합니다.
    청크별로 즉시 SSE 형식으로 구성하여 반환합니다.
    """
    try:
        print(f"스트리밍 생성 시작: 모델={model_id}")
        final_prompt = _build_final_prompt(user_input, chat_history, prompt_cards)
        
        # 동적 토큰 할당
        max_tokens = _calculate_dynamic_max_tokens(len(final_prompt))
        print(f"동적 토큰 할당: {max_tokens}")
        
        # 모델에 따른 요청 본문 구성
        if model_id.startswith("anthropic."):
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.1,
                "top_p": 0.9,
            }
        else:
            # Meta Llama나 Amazon Nova 모델들을 위한 요청 형식
            request_body = {
                "prompt": final_prompt,
                "max_gen_len": 4096,
                "temperature": 0.1,
                "top_p": 0.9,
            }

        # 재시도 로직을 포함한 Bedrock 호출
        response_stream = _invoke_bedrock_with_retry(
            model_id, request_body, max_retries=3
        )
        
        # 최적화된 스트리밍 구현 - 버퍼링 최소화
        sse_chunks = []
        full_response = ""
        
        # 시작 이벤트
        start_data = {
            "response": "",
            "sessionId": "default",
            "type": "start"
        }
        sse_chunks.append(f"data: {json.dumps(start_data)}\n\n")
        
        # 실시간 청크 처리 - 최소 지연
        for event in response_stream.get("body"):
            chunk = json.loads(event["chunk"]["bytes"].decode())
            
            # 모델별 응답 형식 처리
            text = None
            if model_id.startswith("anthropic."):
                # Anthropic 모델 응답 형식
                if chunk['type'] == 'content_block_delta':
                    text = chunk['delta']['text']
            else:
                # Meta Llama나 Amazon Nova 모델 응답 형식
                if 'generation' in chunk:
                    text = chunk['generation']
                elif 'text' in chunk:
                    text = chunk['text']
            
            if text:
                full_response += text
                
                # 즉시 청크 전송 (버퍼링 없음)
                sse_data = {
                    "response": text,
                    "sessionId": "default",
                    "type": "chunk"
                }
                sse_chunks.append(f"data: {json.dumps(sse_data)}\n\n")
        
        # 완료 이벤트 전송
        completion_data = {
            "response": "",
            "sessionId": "default",
            "type": "complete",
            "fullResponse": full_response
        }
        sse_chunks.append(f"data: {json.dumps(completion_data)}\n\n")
        
        print(f"스트리밍 생성 완료: 총 {len(sse_chunks)} 청크 생성됨, 응답 길이={len(full_response)}")
        return {
            "statusCode": 200,
            "headers": _get_sse_headers(),
            "body": "".join(sse_chunks),
            "isBase64Encoded": False
        }
                
    except Exception as e:
        print(f"스트리밍 오류: {traceback.format_exc()}")
        
        # 사용자 친화적 오류 메시지
        error_message = _get_user_friendly_error(str(e))
        
        error_data = {
            "error": error_message,
            "sessionId": "default",
            "type": "error"
        }
        return {
            "statusCode": 500,
            "headers": _get_sse_headers(),
            "body": f"data: {json.dumps(error_data)}\n\n",
            "isBase64Encoded": False
        }

def _handle_standard_generation(user_input, chat_history, prompt_cards, model_id):
    """일반(non-streaming) Bedrock 응답을 처리합니다."""
    try:
        print(f"일반 생성 시작: 모델={model_id}")
        final_prompt = _build_final_prompt(user_input, chat_history, prompt_cards)
        
        # 모델에 따른 요청 본문 구성
        if model_id.startswith("anthropic."):
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 65536,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.1,
                "top_p": 0.9
            }
        else:
            # Meta Llama나 Amazon Nova 모델들을 위한 요청 형식
            request_body = {
                "prompt": final_prompt,
                "max_gen_len": 4096,
                "temperature": 0.1,
                "top_p": 0.9,
            }

        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        response_body = json.loads(response['body'].read())
        
        # 모델별 응답 형식 처리
        if model_id.startswith("anthropic."):
            # Anthropic 모델 응답 형식
            result_text = response_body['content'][0]['text']
        else:
            # Meta Llama나 Amazon Nova 모델 응답 형식
            if 'generation' in response_body:
                result_text = response_body['generation']
            elif 'outputs' in response_body:
                result_text = response_body['outputs'][0]['text']
            else:
                result_text = response_body.get('text', str(response_body))
        
        print(f"일반 생성 완료: 응답 길이={len(result_text)}")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"result": result_text}),
            "isBase64Encoded": False
        }
    except Exception as e:
        print(f"일반 생성 오류: {traceback.format_exc()}")
        return _create_error_response(500, f"Bedrock 호출 오류: {e}")

def _build_final_prompt(user_input, chat_history, prompt_cards):
    """프론트엔드에서 전송된 프롬프트 카드와 채팅 히스토리를 사용하여 최종 프롬프트를 구성합니다."""
    try:
        print(f"프롬프트 구성 시작")
        print(f"전달받은 프롬프트 카드 수: {len(prompt_cards)}")
        print(f"전달받은 채팅 히스토리 수: {len(chat_history)}")
        
        # 프롬프트 카드가 없으면 데이터베이스에서 로드
        if not prompt_cards:
            try:
                from prompt_manager import SimplePromptManager
                
                # 환경 변수에서 설정 가져오기
                prompt_bucket = os.environ.get('PROMPT_BUCKET', '')
                prompt_meta_table = os.environ.get('PROMPT_META_TABLE', '')
                region = os.environ.get('REGION', 'YOUR-REGION')
                
                # 프롬프트 매니저 초기화
                prompt_manager = SimplePromptManager(prompt_bucket, prompt_meta_table, region)
                
                # 모든 활성화된 프롬프트 로드
                loaded_prompts = prompt_manager.load_all_active_prompts()
                print(f"데이터베이스에서 {len(loaded_prompts)}개 프롬프트 로드됨")
                
                # 프롬프트 카드 형식으로 변환
                prompt_cards = []
                for prompt in loaded_prompts:
                    prompt_cards.append({
                        'promptId': prompt['promptId'],
                        'title': prompt['title'],
                        'prompt_text': prompt['content'],
                        'content': prompt['content'],
                        'isActive': prompt['isActive'],
                        'threshold': prompt['threshold']
                    })
                
            except Exception as e:
                print(f"데이터베이스에서 프롬프트 로드 실패: {str(e)}")
                prompt_cards = []
        
        # 프롬프트 카드 처리
        system_prompt_parts = []
        for card in prompt_cards:
            prompt_text = card.get('prompt_text', card.get('content', '')).strip()
            if prompt_text:
                title = card.get('title', 'Untitled')
                print(f"프롬프트 카드 적용: '{title}' ({len(prompt_text)}자)")
                system_prompt_parts.append(prompt_text)
        
        system_prompt = "\n\n".join(system_prompt_parts)
        print(f"시스템 프롬프트 길이: {len(system_prompt)}자")
        
        # 채팅 히스토리 구성
        history_parts = []
        for msg in chat_history:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role and content:
                if role == 'user':
                    history_parts.append(f"Human: {content}")
                elif role == 'assistant':
                    history_parts.append(f"Assistant: {content}")
        
        history_str = "\n\n".join(history_parts)
        print(f"채팅 히스토리 길이: {len(history_str)}자")
        
        # 최종 프롬프트 구성
        prompt_parts = []
        
        # 1. 시스템 프롬프트 (역할, 지침 등)
        if system_prompt:
            prompt_parts.append(system_prompt)
        
        # 2. 대화 히스토리
        if history_str:
            prompt_parts.append(history_str)
        
        # 3. 현재 사용자 입력
        prompt_parts.append(f"Human: {user_input}")
        prompt_parts.append("Assistant:")
        
        final_prompt = "\n\n".join(prompt_parts)
        print(f"최종 프롬프트 길이: {len(final_prompt)}자")
        
        return final_prompt

    except Exception as e:
        print(f"프롬프트 구성 오류: {traceback.format_exc()}")
        # 오류 발생 시 기본 프롬프트 반환 (히스토리 포함)
        try:
            history_str = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            if history_str:
                return f"{history_str}\n\nHuman: {user_input}\n\nAssistant:"
            else:
                return f"Human: {user_input}\n\nAssistant:"
        except:
            return f"Human: {user_input}\n\nAssistant:"

def _get_sse_headers():
    """Server-Sent Events 응답을 위한 헤더를 반환합니다."""
    return {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no'  # NGINX 버퍼링 비활성화
    }

def _preprocess_long_content(content):
    """긴 콘텐츠 전처리 및 최적화"""
    try:
        content_length = len(content)
        print(f"입력 콘텐츠 길이: {content_length:,}자")
        
        # 기본 길이 체크
        if content_length <= MAX_INPUT_LENGTH:
            return content
        
        # 너무 긴 콘텐츠 처리
        if content_length > MAX_INPUT_LENGTH * 3:  # 450K 문자 초과
            return {
                'error': f"입력이 너무 깁니다. 최대 {MAX_INPUT_LENGTH * 3:,}자까지 지원됩니다. 현재: {content_length:,}자"
            }
        
        print(f"긴 콘텐츠 감지 - 요약 생성 모드로 전환")
        
        # XML 기사 형식 감지 및 처리
        if '<article>' in content and '</article>' in content:
            return _process_article_content(content)
        
        # 일반 긴 텍스트 처리
        return _truncate_content(content)
        
    except Exception as e:
        print(f"콘텐츠 전처리 오류: {e}")
        return content[:MAX_INPUT_LENGTH]  # 안전한 폴백

def _process_article_content(content):
    """기사 XML 콘텐츠 처리"""
    try:
        # 기사별로 분리
        articles = content.split('<article>')
        processed_articles = []
        total_length = 0
        
        for article in articles[1:]:  # 첫 번째는 비어있음
            if '</article>' in article:
                article_content = article.split('</article>')[0]
                
                # 핵심 정보만 추출
                title = _extract_between_tags(article_content, 'title')
                content_text = _extract_between_tags(article_content, 'content')
                
                if title and content_text:
                    # 콘텐츠 요약 (500자 제한)
                    summary = content_text[:500] + '...' if len(content_text) > 500 else content_text
                    article_summary = f"[제목] {title}\n[내용] {summary}"
                    
                    if total_length + len(article_summary) > MAX_INPUT_LENGTH:
                        break
                    
                    processed_articles.append(article_summary)
                    total_length += len(article_summary)
        
        result = "\n\n".join(processed_articles)
        print(f"기사 {len(processed_articles)}개 처리 완료, 최종 길이: {len(result):,}자")
        return result
        
    except Exception as e:
        print(f"기사 콘텐츠 처리 오류: {e}")
        return _truncate_content(content)

def _extract_between_tags(text, tag):
    """태그 사이의 텍스트 추출"""
    try:
        start_tag = f'<{tag}>'
        end_tag = f'</{tag}>'
        start_idx = text.find(start_tag)
        if start_idx == -1:
            return None
        start_idx += len(start_tag)
        end_idx = text.find(end_tag, start_idx)
        if end_idx == -1:
            return None
        return text[start_idx:end_idx].strip()
    except:
        return None

def _truncate_content(content):
    """일반 콘텐츠 절단"""
    truncated = content[:MAX_INPUT_LENGTH]
    print(f"콘텐츠 절단: {len(content):,}자 -> {len(truncated):,}자")
    return truncated + "\n\n[콘텐츠가 너무 길어 일부만 처리되었습니다]"

def _calculate_dynamic_max_tokens(input_length):
    """입력 길이에 따른 동적 토큰 계산"""
    # 대략적인 토큰 추정 (1토큰 = 4문자)
    estimated_input_tokens = input_length // 4
    
    # 최대 출력 토큰 계산 (입력 + 출력 < 200K)
    max_output_tokens = min(8192, MAX_TOTAL_TOKENS - estimated_input_tokens)
    
    # 최소 보장 토큰
    if max_output_tokens < 1024:
        max_output_tokens = 1024
        print(f"경고: 입력이 너무 깁니다. 최소 출력 토큰만 할당")
    
    print(f"토큰 계산: 입력 {estimated_input_tokens:,}, 출력 {max_output_tokens:,}")
    return max_output_tokens

def _invoke_bedrock_with_retry(model_id, request_body, max_retries=3):
    """재시도 로직을 포함한 Bedrock API 호출"""
    import time
    
    for attempt in range(max_retries):
        try:
            return bedrock_client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body)
            )
        except Exception as e:
            error_str = str(e)
            print(f"시도 {attempt + 1}/{max_retries} 실패: {error_str}")
            
            # 토큰 제한 오류 시 토큰 감소 후 재시도
            if "token" in error_str.lower() and "limit" in error_str.lower():
                if attempt < max_retries - 1:
                    current_tokens = request_body.get("max_tokens", 4096)
                    new_tokens = int(current_tokens * 0.7)  # 30% 감소
                    request_body["max_tokens"] = max(1024, new_tokens)
                    print(f"토큰 감소: {current_tokens} -> {new_tokens}")
                    time.sleep(1)  # 1초 대기
                    continue
            
            # 마지막 시도에서 실패 시 예외 발생
            if attempt == max_retries - 1:
                raise e
            
            # 지수 백오프
            time.sleep(2 ** attempt)

def _get_user_friendly_error(error_str):
    """사용자 친화적 오류 메시지 생성"""
    error_lower = error_str.lower()
    
    if "token" in error_lower and "limit" in error_lower:
        return "입력이 너무 깁니다. 더 짧은 텍스트로 다시 시도해주세요."
    elif "timeout" in error_lower:
        return "요청 시간이 초과되었습니다. 더 짧은 텍스트로 다시 시도해주세요."
    elif "throttl" in error_lower:
        return "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
    else:
        return "일시적인 오류가 발생했습니다. 다시 시도해주세요."

def _handle_batch_processing(user_input, chat_history, prompt_cards, model_id):
    """대용량 문서 배치 처리"""
    try:
        import uuid
        import boto3
        
        # SQS 클라이언트 초기화
        sqs = boto3.client('sqs', region_name=os.environ.get('REGION'))
        dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION'))
        
        batch_queue_url = os.environ.get('BATCH_QUEUE_URL')
        batch_jobs_table_name = os.environ.get('BATCH_JOBS_TABLE')
        
        if not batch_queue_url or not batch_jobs_table_name:
            return _create_error_response(500, "배치 처리 시스템이 설정되지 않았습니다.")
        
        # 작업 ID 생성
        job_id = str(uuid.uuid4())
        
        # 콘텐츠를 청크로 분할
        chunks = _split_content_into_chunks(user_input)
        
        # 프롬프트 구성
        final_prompt = _build_final_prompt("", chat_history, prompt_cards)
        
        # 각 청크를 SQS로 전송
        batch_jobs_table = dynamodb.Table(batch_jobs_table_name)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i}"
            
            # 작업 상태 저장
            batch_jobs_table.put_item(
                Item={
                    'job_id': f"{job_id}#{chunk_id}",
                    'status': 'queued',
                    'created_at': datetime.utcnow().isoformat(),
                    'ttl': int((datetime.utcnow().timestamp() + 86400))  # 24시간 TTL
                }
            )
            
            # SQS 메시지 전송
            message = {
                'job_id': job_id,
                'chunk_id': chunk_id,
                'content': chunk,
                'prompt': final_prompt,
                'model_id': model_id
            }
            
            sqs.send_message(
                QueueUrl=batch_queue_url,
                MessageBody=json.dumps(message)
            )
        
        print(f"배치 작업 시작: job_id={job_id}, chunks={len(chunks)}")
        
        return {
            "statusCode": 202,  # Accepted
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "대용량 문서 배치 처리가 시작되었습니다.",
                "job_id": job_id,
                "total_chunks": len(chunks),
                "estimated_time": f"{len(chunks) * 2}분 예상"
            })
        }
        
    except Exception as e:
        print(f"배치 처리 오류: {traceback.format_exc()}")
        return _create_error_response(500, f"배치 처리 오류: {str(e)}")

def _split_content_into_chunks(content, chunk_size=50000):
    """콘텐츠를 청크로 분할"""
    try:
        # XML 기사 형식 감지
        if '<article>' in content and '</article>' in content:
            return _split_articles_into_chunks(content)
        
        # 일반 텍스트 분할
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append(chunk)
        
        return chunks
        
    except Exception as e:
        print(f"청크 분할 오류: {e}")
        return [content[:chunk_size]]  # 안전한 폴백

def _split_articles_into_chunks(content, articles_per_chunk=10):
    """기사별로 청크 분할"""
    try:
        articles = content.split('<article>')[1:]  # 첫 번째는 비어있음
        chunks = []
        
        for i in range(0, len(articles), articles_per_chunk):
            chunk_articles = articles[i:i + articles_per_chunk]
            chunk_content = '<articles>\n'
            
            for article in chunk_articles:
                if '</article>' in article:
                    chunk_content += '<article>' + article
            
            chunk_content += '\n</articles>'
            chunks.append(chunk_content)
        
        print(f"기사 {len(articles)}개를 {len(chunks)}개 청크로 분할")
        return chunks
        
    except Exception as e:
        print(f"기사 청크 분할 오류: {e}")
        return [content[:50000]]  # 안전한 폴백

def _create_error_response(status_code, message):
    """일반적인 JSON 오류 응답을 생성합니다."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message, "timestamp": datetime.utcnow().isoformat()}),
        "isBase64Encoded": False
        }

def _handle_s3_upload_request(event):
    """S3 presigned URL 생성 for 대용량 파일 업로드"""
    try:
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('LARGE_FILE_BUCKET', 'title-generator-large-files')
        
        # 고유한 파일 키 생성
        import uuid
        file_key = f"uploads/{datetime.utcnow().strftime('%Y%m%d')}/{uuid.uuid4()}.txt"
        
        # Presigned URL 생성 (5분 유효)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket_name, 'Key': file_key},
            ExpiresIn=300
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "uploadUrl": presigned_url,
                "fileKey": file_key,
                "expiresIn": 300
            })
        }
    except Exception as e:
        print(f"S3 업로드 URL 생성 오류: {e}")
        return _create_error_response(500, "파일 업로드 URL 생성 실패")

def _handle_s3_process_request(event):
    """S3에 업로드된 대용량 파일 처리"""
    try:
        body = json.loads(event.get('body', '{}'))
        file_key = body.get('fileKey')
        model_id = body.get('modelId', DEFAULT_MODEL_ID)
        chat_history = body.get('chat_history', [])
        prompt_cards = body.get('prompt_cards', [])
        
        if not file_key:
            return _create_error_response(400, "파일 키가 필요합니다.")
        
        # S3에서 파일 읽기
        s3_client = boto3.client('s3')
        bucket_name = os.environ.get('LARGE_FILE_BUCKET', 'title-generator-large-files')
        
        obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        content = obj['Body'].read().decode('utf-8')
        
        print(f"S3 파일 읽기 완료: {len(content):,}자")
        
        # 병렬 처리를 위한 작업 생성
        return _create_parallel_processing_jobs(content, chat_history, prompt_cards, model_id)
        
    except Exception as e:
        print(f"S3 파일 처리 오류: {e}")
        return _create_error_response(500, "파일 처리 실패")

def _create_parallel_processing_jobs(content, chat_history, prompt_cards, model_id):
    """대용량 콘텐츠를 병렬 처리를 위한 작업으로 분할"""
    try:
        import uuid
        job_id = str(uuid.uuid4())
        
        # Step Functions 클라이언트
        sfn_client = boto3.client('stepfunctions')
        state_machine_arn = os.environ.get('PARALLEL_PROCESSING_STATE_MACHINE')
        
        if not state_machine_arn:
            # Step Functions가 없으면 기존 배치 처리 사용
            return _handle_batch_processing(content, chat_history, prompt_cards, model_id)
        
        # 콘텐츠를 병렬 처리 가능한 청크로 분할
        chunks = _split_for_parallel_processing(content)
        
        # Step Functions 실행
        execution_input = {
            'jobId': job_id,
            'chunks': chunks,
            'chatHistory': chat_history,
            'promptCards': prompt_cards,
            'modelId': model_id,
            'processingType': 'parallel'
        }
        
        response = sfn_client.start_execution(
            stateMachineArn=state_machine_arn,
            name=f"parallel-processing-{job_id}",
            input=json.dumps(execution_input)
        )
        
        return {
            "statusCode": 202,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "병렬 처리가 시작되었습니다.",
                "jobId": job_id,
                "executionArn": response['executionArn'],
                "chunks": len(chunks),
                "estimatedTime": f"{len(chunks) * 0.5}분 예상"
            })
        }
        
    except Exception as e:
        print(f"병렬 처리 작업 생성 오류: {e}")
        return _handle_batch_processing(content, chat_history, prompt_cards, model_id)

def _split_for_parallel_processing(content, chunk_size=30000):
    """병렬 처리를 위한 스마트 청크 분할"""
    chunks = []
    
    # XML 기사 형식 감지
    if '<article>' in content and '</article>' in content:
        # 기사별로 분할
        articles = content.split('<article>')[1:]
        current_chunk = []
        current_size = 0
        
        for article in articles:
            if '</article>' in article:
                article_content = '<article>' + article
                article_size = len(article_content)
                
                if current_size + article_size > chunk_size and current_chunk:
                    chunks.append({'content': ''.join(current_chunk), 'type': 'articles'})
                    current_chunk = [article_content]
                    current_size = article_size
                else:
                    current_chunk.append(article_content)
                    current_size += article_size
        
        if current_chunk:
            chunks.append({'content': ''.join(current_chunk), 'type': 'articles'})
    else:
        # 일반 텍스트: 문단 기준으로 스마트 분할
        paragraphs = content.split('\n\n')
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > chunk_size and current_chunk:
                chunks.append({'content': '\n\n'.join(current_chunk), 'type': 'text'})
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append({'content': '\n\n'.join(current_chunk), 'type': 'text'})
    
    print(f"병렬 처리를 위해 {len(chunks)}개 청크로 분할")
    return chunks 