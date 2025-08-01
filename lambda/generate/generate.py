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
bedrock_client = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "us-east-1"))
dynamodb_client = boto3.client("dynamodb", region_name=os.environ.get("REGION", "us-east-1"))
PROMPT_META_TABLE = os.environ.get("PROMPT_META_TABLE", "BedrockDiyPrompts")
# 기본 모델 ID (프론트엔드에서 지정하지 않을 때 사용)
DEFAULT_MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

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
        
        # 모델에 따른 요청 본문 구성
        if model_id.startswith("anthropic."):
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 65536,
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

        response_stream = bedrock_client.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(request_body)
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
        error_data = {
            "error": str(e),
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
                prompt_bucket = os.environ.get('PROMPT_BUCKET', 'title-generator-prompts')
                prompt_meta_table = os.environ.get('PROMPT_META_TABLE', 'title-generator-prompt-meta')
                region = os.environ.get('REGION', 'us-east-1')
                
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

def _create_error_response(status_code, message):
    """일반적인 JSON 오류 응답을 생성합니다."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message, "timestamp": datetime.utcnow().isoformat()}),
        "isBase64Encoded": False
        } 