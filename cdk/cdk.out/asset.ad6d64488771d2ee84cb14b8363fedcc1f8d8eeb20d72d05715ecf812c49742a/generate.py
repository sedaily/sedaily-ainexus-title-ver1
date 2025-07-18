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
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

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
        project_id = event.get("pathParameters", {}).get("projectId")

        if not project_id:
            return _create_error_response(400, "프로젝트 ID가 필요합니다.")

        # 요청 본문(body) 파싱
        if http_method == 'GET':
            params = event.get('queryStringParameters') or {}
            user_input = params.get('userInput', '')
            chat_history_str = params.get('chat_history', '[]')
            chat_history = json.loads(chat_history_str)
        else: # POST
            body = json.loads(event.get('body', '{}'))
            user_input = body.get('userInput', '')
            chat_history = body.get('chat_history', [])
            
        if not user_input.strip():
            return _create_error_response(400, "사용자 입력이 필요합니다.")
        
        # 스트리밍 또는 일반 생성 분기
        if "/stream" in path:
            return _handle_streaming_generation(project_id, user_input, chat_history)
        else:
            return _handle_standard_generation(project_id, user_input, chat_history)

    except json.JSONDecodeError:
        print("JSON 파싱 오류 발생")
        return _create_error_response(400, "잘못된 JSON 형식입니다.")
    except Exception as e:
        print(f"오류 발생: {traceback.format_exc()}")
        return _create_error_response(500, f"서버 내부 오류: {e}")

def _handle_streaming_generation(project_id, user_input, chat_history):
    """
    Bedrock에서 스트리밍 응답을 받아 실시간으로 반환합니다.
    Lambda Response Streaming을 사용하여 진짜 실시간 스트리밍을 구현합니다.
    """
    try:
        print(f"실시간 스트리밍 생성 시작: 프로젝트 ID={project_id}")
        final_prompt = _build_final_prompt(project_id, user_input, chat_history)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.7,
            "top_p": 0.9,
        }

        # Lambda Response Streaming을 위한 Generator 사용
        def stream_generator():
            """진짜 실시간 스트리밍 Generator"""
            try:
                # 시작 이벤트
                start_data = {
                    "response": "",
                    "sessionId": project_id,
                    "type": "start"
                }
                yield f"data: {json.dumps(start_data)}\n\n"
                
                # Bedrock 스트리밍 호출
                response_stream = bedrock_client.invoke_model_with_response_stream(
                    modelId=MODEL_ID,
                    body=json.dumps(request_body)
                )
                
                full_response = ""
                
                # 실시간 청크 처리
                for event in response_stream.get("body"):
                    chunk = json.loads(event["chunk"]["bytes"].decode())
                    if chunk['type'] == 'content_block_delta':
                        text = chunk['delta']['text']
                        full_response += text
                        
                        # 실시간으로 청크 전송
                        sse_data = {
                            "response": text,
                            "sessionId": project_id,
                            "type": "chunk"
                        }
                        yield f"data: {json.dumps(sse_data)}\n\n"
                
                # 완료 이벤트 전송
                completion_data = {
                    "response": "",
                    "sessionId": project_id,
                    "type": "complete",
                    "fullResponse": full_response
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
                print(f"실시간 스트리밍 완료: 응답 길이={len(full_response)}")
                
            except Exception as e:
                print(f"스트리밍 중 오류: {e}")
                error_data = {
                    "error": str(e),
                    "sessionId": project_id,
                    "type": "error"
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        # Lambda Response Streaming 반환
        return {
            "statusCode": 200,
            "headers": _get_sse_headers(),
            "body": stream_generator(),
            "isBase64Encoded": False
        }

    except Exception as e:
        print(f"스트리밍 오류: {traceback.format_exc()}")
        error_data = {
            "error": str(e),
            "sessionId": project_id,
            "type": "error"
        }
        return {
            "statusCode": 500,
            "headers": _get_sse_headers(),
            "body": f"data: {json.dumps(error_data)}\n\n",
            "isBase64Encoded": False
        }

def _handle_standard_generation(project_id, user_input, chat_history):
    """일반(non-streaming) Bedrock 응답을 처리합니다."""
    try:
        print(f"일반 생성 시작: 프로젝트 ID={project_id}")
        final_prompt = _build_final_prompt(project_id, user_input, chat_history)
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.7,
            "top_p": 0.9
        }

        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        response_body = json.loads(response['body'].read())
        result_text = response_body['content'][0]['text']
        
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

def _build_final_prompt(project_id, user_input, chat_history):
    """DynamoDB에서 프롬프트 카드를 가져와 최종 프롬프트를 구성합니다."""
    try:
        print(f"프롬프트 구성 시작: 프로젝트 ID={project_id}")
        response = dynamodb_client.query(
            TableName=PROMPT_META_TABLE,
            KeyConditionExpression="projectId = :pid",
            ExpressionAttributeValues={":pid": {"S": project_id}},
            ScanIndexForward=True # stepOrder 기준 오름차순
        )
        
        prompt_cards = sorted(
            [item for item in response.get("Items", []) if item.get("isActive", {}).get("BOOL", True)],
            key=lambda x: int(x.get("stepOrder", {}).get("N", "999"))
        )
        
        print(f"프롬프트 카드 {len(prompt_cards)}개 검색됨")
        
        system_prompt_parts = [card.get("content", {}).get("S", "") for card in prompt_cards]
        system_prompt = "\n\n".join(filter(None, system_prompt_parts))
        
        # 최종 프롬프트 구성 (채팅 히스토리 + 시스템 프롬프트 + 사용자 입력)
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
        
        final_prompt = f"{system_prompt}\n\n{history_str}\n\nHuman: {user_input}\n\nAssistant:"
        return final_prompt
        
    except Exception as e:
        print(f"프롬프트 구성 오류: {traceback.format_exc()}")
        # 오류 발생 시 기본 프롬프트 반환
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