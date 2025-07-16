"""
AI 대화 생성 Lambda 함수 (LangChain 적용 버전)
- Runnable과 Memory를 사용하여 대화 기억 기능 구현
- 확장성과 유지보수성이 높은 구조
"""
import json
import os
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

import boto3

# --- 기본 설정 ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ['REGION']

# 온디맨드 및 스트리밍 지원 모델 정의
SUPPORTED_MODELS = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "name": "Claude 3 Sonnet",
        "supports_streaming": True,
        "supports_ondemand": True,
        "max_tokens": 4096,
        "context_window": 200000
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "name": "Claude 3 Haiku",
        "supports_streaming": True,
        "supports_ondemand": True,
        "max_tokens": 4096,
        "context_window": 200000
    },
    "anthropic.claude-3-opus-20240229-v1:0": {
        "name": "Claude 3 Opus",
        "supports_streaming": True,
        "supports_ondemand": True,
        "max_tokens": 4096,
        "context_window": 200000
    }
}

# 기본 모델을 온디맨드와 스트리밍을 모두 지원하는 Claude 3 Sonnet으로 설정
DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def get_model_info(model_id):
    """모델 정보를 반환합니다."""
    return SUPPORTED_MODELS.get(model_id, {
        "name": "Unknown Model",
        "supports_streaming": False,
        "supports_ondemand": False,
        "max_tokens": 4096,
        "context_window": 100000
    })

# --- Bedrock 클라이언트 초기화 ---
bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)

ANTHROPIC_VERSION = "bedrock-2023-05-31"

# 스트리밍 응답 처리 함수
def process_streaming_response(streaming_response):
    """스트리밍 응답을 처리하여 완전한 텍스트를 반환합니다."""
    complete_response = ""
    
    try:
        for event in streaming_response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            
            if chunk["type"] == "content_block_delta":
                text_delta = chunk["delta"].get("text", "")
                complete_response += text_delta
                
            elif chunk["type"] == "message_stop":
                logger.info("스트리밍 응답 완료")
                break
                
    except Exception as e:
        logger.error(f"스트리밍 처리 오류: {str(e)}")
        # 스트리밍 실패 시 기본 방식으로 폴백
        return None
        
    return complete_response

# --- 유틸리티 함수 ---
def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

def calculate_dynamic_max_tokens(user_input: str, system_prompt: str = "", model_id: str = DEFAULT_MODEL_ID) -> int:
    """긴 텍스트 처리를 위해 토큰 수를 동적으로 계산하되, 모델 한계를 고려합니다."""
    input_length = len(user_input)
    system_length = len(system_prompt)
    
    # 모델 정보 가져오기
    model_info = get_model_info(model_id)
    model_max_tokens = model_info["max_tokens"]
    
    # 기본 최소값
    base_tokens = 2048
    
    # 입력 길이에 따른 동적 조정 - 더 관대하게
    if input_length < 1000:
        dynamic_tokens = base_tokens
    elif input_length < 3000:
        dynamic_tokens = base_tokens * 2  # 4096
    elif input_length < 8000:
        dynamic_tokens = base_tokens * 3  # 6144
    elif input_length < 15000:
        dynamic_tokens = base_tokens * 4  # 8192
    else:
        dynamic_tokens = base_tokens * 5  # 10240
    
    # 시스템 프롬프트 길이 고려 - 더 관대하게
    if system_length > 5000:
        dynamic_tokens = max(dynamic_tokens, base_tokens * 2)  # 최소 4096 보장
    
    # 모델의 최대 토큰 제한 적용
    max_tokens = min(dynamic_tokens, model_max_tokens)
    
    logger.info(f"토큰 계산 - 모델: {model_info['name']}, 입력길이: {input_length}, 시스템길이: {system_length}, 할당토큰: {max_tokens}")
    return max_tokens

def log_performance_metrics(operation: str, start_time: float, **kwargs):
    """성능 메트릭을 로깅합니다."""
    execution_time = time.time() - start_time
    
    metrics = {
        "operation": operation,
        "execution_time_seconds": round(execution_time, 3),
        "timestamp": datetime.utcnow().isoformat(),
        **kwargs
    }
    
    logger.info(f"성능 메트릭: {json.dumps(metrics, ensure_ascii=False)}")
    return execution_time

# --- 메인 핸들러 ---
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    request_start_time = time.time()
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': get_cors_headers(), 'body': ''}

    try:
        logger.info(f"요청 시작 - RequestId: {context.aws_request_id}")
        
        body = json.loads(event.get('body', '{}'))
        path_params = event.get('pathParameters', {}) or {}
        
        project_id = path_params.get('projectId')
        user_input = body.get('userInput', '').strip()
        chat_history = body.get('chat_history', []) # 프론트에서 이전 대화 기록을 받아옴

        if not project_id or not user_input:
            logger.warning(f"잘못된 요청 - project_id: {project_id}, user_input 길이: {len(user_input) if user_input else 0}")
            return {'statusCode': 400, 'headers': get_cors_headers(), 'body': json.dumps({'message': '프로젝트 ID와 사용자 입력은 필수입니다.'})}

        logger.info(f"요청 상세 - 프로젝트: {project_id}, 입력길이: {len(user_input)}, 히스토리: {len(chat_history)}개")

        # --- 동적 시스템 프롬프트 로드 ---
        prompt_load_start = time.time()
        from prompt_manager import SimplePromptManager
        prompt_manager = SimplePromptManager(
            prompt_bucket=os.environ.get('PROMPT_BUCKET', ''),
            prompt_meta_table=os.environ.get('PROMPT_META_TABLE', ''),
            region=REGION
        )
        prompts = prompt_manager.load_project_prompts(project_id)
        system_prompt = prompt_manager.combine_prompts(prompts, mode="system")
        
        log_performance_metrics("prompt_loading", prompt_load_start, 
                               prompt_count=len(prompts), 
                               system_prompt_length=len(system_prompt))

        # --- 동적 토큰 계산 ---
        max_tokens = calculate_dynamic_max_tokens(user_input, system_prompt, DEFAULT_MODEL_ID)

        # 모델 정보 가져오기
        model_info = get_model_info(DEFAULT_MODEL_ID)
        supports_streaming = model_info["supports_streaming"]
        supports_ondemand = model_info["supports_ondemand"]
        
        if not supports_ondemand:
            logger.error(f"모델 {DEFAULT_MODEL_ID}는 온디맨드 호출을 지원하지 않습니다")
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': f'현재 모델({model_info["name"]})은 온디맨드 호출을 지원하지 않습니다. 관리자에게 문의하세요.',
                    'error_type': 'ModelNotSupported'
                }, ensure_ascii=False)
            }

        # --- Bedrock 메시지 포맷 구성 (InvokeModel API 공식 사양 준수) ---
        message_processing_start = time.time()
        
        # 1. 모든 메시지를 하나로 합치고, 역할이 같은 연속 메시지를 병합합니다.
        all_inputs = chat_history + [{"role": "user", "content": user_input}]
        
        merged_messages = []
        for msg in all_inputs:
            role = msg.get("role")
            content = msg.get("content", "").strip()

            if not content or role not in ["user", "assistant"]:
                continue

            if merged_messages and merged_messages[-1]["role"] == role:
                merged_messages[-1]["content"] += "\\n\\n" + content
            else:
                merged_messages.append({"role": role, "content": content})

        # 2. 대화가 assistant로 시작하는 경우를 방지합니다.
        if merged_messages and merged_messages[0]["role"] == "assistant":
            merged_messages.pop(0)

        # 3. 긴 대화 히스토리 최적화 - 최근 20개 메시지만 유지하되 중요한 컨텍스트 보존
        if len(merged_messages) > 20:
            # 첫 번째 메시지(중요한 컨텍스트)와 최근 19개 메시지 유지
            first_message = merged_messages[0]
            recent_messages = merged_messages[-19:]
            merged_messages = [first_message] + recent_messages
            logger.info(f"긴 대화 히스토리 최적화: {len(all_inputs)} -> {len(merged_messages)} 메시지")

        # 4. 최종적으로 API 형식에 맞게 content를 객체 배열로 변환합니다.
        final_api_messages = []
        for msg in merged_messages:
            final_api_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            })
        
        messages = final_api_messages
        
        log_performance_metrics("message_processing", message_processing_start, 
                               original_messages=len(all_inputs), 
                               merged_messages=len(merged_messages))

        # --- Bedrock 호출 ---
        bedrock_start_time = time.time()
        logger.info(f"Bedrock 호출 시작 - 프로젝트: {project_id}, 모델: {model_info['name']} ({DEFAULT_MODEL_ID}), 최대토큰: {max_tokens}")
        
        body = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": max_tokens,  # 동적으로 계산된 토큰 수 사용
            "temperature": 0.7,
            "messages": messages,
        }
        if system_prompt:
            body["system"] = system_prompt
        
        # --- 진단용 로그: Bedrock에 전달할 최종 body를 출력합니다 ---
        logger.info(f"Bedrock 요청 상세: 메시지수={len(messages)}, 시스템프롬프트길이={len(system_prompt)}, 최대토큰={max_tokens}, 스트리밍지원={supports_streaming}")

        # 재시도 로직 추가
        max_retries = 3
        response_content = None
        
        for attempt in range(max_retries):
            try:
                # 스트리밍 지원 여부 확인 후 시도
                if attempt == 0 and supports_streaming:
                    logger.info("스트리밍 방식으로 Bedrock 호출 시도")
                    try:
                        streaming_response = bedrock_client.invoke_model_with_response_stream(
                            modelId=DEFAULT_MODEL_ID,
                            contentType="application/json",
                            accept="application/json",
                            body=json.dumps(body).encode("utf-8"),
                        )
                        
                        response_content = process_streaming_response(streaming_response)
                        
                        if response_content:
                            logger.info("스트리밍 방식 성공")
                            break
                        else:
                            logger.warning("스트리밍 처리 실패, 일반 방식으로 폴백")
                            
                    except Exception as streaming_error:
                        logger.warning(f"스트리밍 호출 실패: {str(streaming_error)}, 일반 방식으로 폴백")
                
                # 일반 방식으로 호출
                logger.info("일반 방식으로 Bedrock 호출")
                response = bedrock_client.invoke_model(
                    modelId=DEFAULT_MODEL_ID,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(body).encode("utf-8"),
                )
                
                response_json = json.loads(response["body"].read())
                response_content = response_json["content"][0]["text"]
                break  # 성공하면 루프 탈출
                
            except Exception as e:
                logger.warning(f"Bedrock 호출 시도 {attempt + 1}/{max_retries} 실패: {str(e)}")
                
                if attempt == max_retries - 1:  # 마지막 시도
                    raise e
                    
                # 토큰 제한 오류인 경우 토큰 수를 줄여서 재시도
                if "token" in str(e).lower() or "length" in str(e).lower():
                    max_tokens = int(max_tokens * 0.7)  # 30% 줄임
                    body["max_tokens"] = max_tokens
                    logger.info(f"토큰 수를 {max_tokens}로 줄여서 재시도")
                
                time.sleep(2 ** attempt)  # 지수 백오프

        bedrock_execution_time = log_performance_metrics("bedrock_invoke", bedrock_start_time)
        
        if not response_content:
            raise Exception("Bedrock에서 응답을 받지 못했습니다")
        
        response_length = len(response_content)
        
        logger.info(f"Bedrock 응답 완료 - 응답길이: {response_length}자, 실행시간: {bedrock_execution_time:.2f}초")

        # 전체 요청 처리 시간 로그
        total_execution_time = log_performance_metrics("total_request", request_start_time,
                                                     project_id=project_id,
                                                     input_length=len(user_input),
                                                     response_length=response_length,
                                                     max_tokens_used=max_tokens,
                                                     model_id=DEFAULT_MODEL_ID)

        # 성공 응답 반환
        response_body = {
            'message': '응답이 생성되었습니다.',
            'result': response_content,
            'projectId': project_id,
            'mode': 'prompt_based' if prompts else 'direct_conversation',
            'model_info': {
                'model_used': DEFAULT_MODEL_ID,
                'model_name': model_info['name'],
                'max_tokens': max_tokens,
                'supports_streaming': supports_streaming,
                'supports_ondemand': supports_ondemand,
                'execution_time': round(total_execution_time, 2)
            },
            'performance_metrics': {
                'total_time': round(total_execution_time, 2),
                'bedrock_time': round(bedrock_execution_time, 2),
                'input_length': len(user_input),
                'output_length': response_length
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response_body, ensure_ascii=False)
        }

    except Exception as e:
        error_time = log_performance_metrics("error_handling", request_start_time, 
                                           error_type=type(e).__name__, 
                                           error_message=str(e))
        
        logger.error(f"핸들러 오류 (실행시간: {error_time:.2f}초): {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': f'서버 오류: {str(e)}',
                'error_type': type(e).__name__,
                'execution_time': round(error_time, 2),
                'model_info': {
                    'model_used': DEFAULT_MODEL_ID,
                    'model_name': get_model_info(DEFAULT_MODEL_ID)['name']
                }
            }, ensure_ascii=False)
        } 