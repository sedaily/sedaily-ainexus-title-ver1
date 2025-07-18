"""
WebSocket 실시간 스트리밍 Lambda 함수
"""
import json
import os
import boto3
import traceback
from datetime import datetime

# AWS 클라이언트
bedrock_client = boto3.client("bedrock-runtime")
dynamodb_client = boto3.client("dynamodb")
apigateway_client = boto3.client("apigatewaymanagementapi")

# 환경 변수
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE')
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET')
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def handler(event, context):
    """
    WebSocket 스트리밍 메시지 처리
    """
    try:
        connection_id = event['requestContext']['connectionId']
        domain_name = event['requestContext']['domainName']
        stage = event['requestContext']['stage']
        
        # API Gateway Management API 클라이언트 설정
        endpoint_url = f"https://{domain_name}/{stage}"
        global apigateway_client
        apigateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=endpoint_url
        )
        
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        if action == 'stream':
            return handle_stream_request(connection_id, body)
        else:
            return send_error(connection_id, "지원하지 않는 액션입니다")
            
    except Exception as e:
        print(f"WebSocket 처리 오류: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_stream_request(connection_id, data):
    """
    실시간 스트리밍 요청 처리
    """
    try:
        project_id = data.get('projectId')
        user_input = data.get('userInput')
        chat_history = data.get('chat_history', [])
        
        if not project_id or not user_input:
            return send_error(connection_id, "프로젝트 ID와 사용자 입력이 필요합니다")
        
        # 1단계: 프롬프트 구성 시작
        send_message(connection_id, {
            "type": "progress",
            "step": "🔧 프롬프트 카드를 분석하고 있습니다...",
            "progress": 10,
            "sessionId": project_id
        })
        
        # 프롬프트 구성
        final_prompt = build_final_prompt(project_id, user_input, chat_history)
        
        # 2단계: AI 모델 준비
        send_message(connection_id, {
            "type": "progress", 
            "step": "🤖 AI 모델을 준비하고 있습니다...",
            "progress": 25,
            "sessionId": project_id
        })
        
        # Bedrock 스트리밍 요청
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.7,
            "top_p": 0.9,
        }
        
        # 3단계: 스트리밍 시작
        send_message(connection_id, {
            "type": "progress",
            "step": "✍️ AI가 응답을 실시간으로 생성하고 있습니다...",
            "progress": 40,
            "sessionId": project_id
        })
        
        # Bedrock 스트리밍 응답 처리
        response_stream = bedrock_client.invoke_model_with_response_stream(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        full_response = ""
        
        # 실시간 청크 전송
        for event in response_stream.get("body"):
            chunk = json.loads(event["chunk"]["bytes"].decode())
            
            if chunk['type'] == 'content_block_delta':
                text = chunk['delta']['text']
                full_response += text
                
                # 즉시 클라이언트로 전송
                send_message(connection_id, {
                    "type": "stream_chunk",
                    "content": text,
                    "sessionId": project_id
                })
        
        # 4단계: 스트리밍 완료
        send_message(connection_id, {
            "type": "progress",
            "step": "✅ 응답 생성이 완료되었습니다!",
            "progress": 100,
            "sessionId": project_id
        })
        
        # 최종 완료 알림
        send_message(connection_id, {
            "type": "stream_complete", 
            "fullContent": full_response,
            "sessionId": project_id
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': '스트리밍 완료'})
        }
        
    except Exception as e:
        print(f"스트리밍 처리 오류: {traceback.format_exc()}")
        send_error(connection_id, f"스트리밍 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def build_final_prompt(project_id, user_input, chat_history):
    """
    DynamoDB에서 프롬프트 카드를 가져와 최종 프롬프트 구성
    """
    try:
        response = dynamodb_client.query(
            TableName=PROMPT_META_TABLE,
            KeyConditionExpression="projectId = :pid",
            ExpressionAttributeValues={":pid": {"S": project_id}},
            ScanIndexForward=True
        )
        
        prompt_cards = sorted(
            [item for item in response.get("Items", []) if item.get("isActive", {}).get("BOOL", True)],
            key=lambda x: int(x.get("stepOrder", {}).get("N", "999"))
        )
        
        system_prompt_parts = [card.get("content", {}).get("S", "") for card in prompt_cards]
        system_prompt = "\n\n".join(filter(None, system_prompt_parts))
        
        # 채팅 히스토리 구성
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
        
        final_prompt = f"{system_prompt}\n\n{history_str}\n\nHuman: {user_input}\n\nAssistant:"
        return final_prompt
        
    except Exception as e:
        print(f"프롬프트 구성 오류: {traceback.format_exc()}")
        return f"Human: {user_input}\n\nAssistant:"

def send_message(connection_id, message):
    """
    WebSocket 클라이언트로 메시지 전송
    """
    try:
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except Exception as e:
        print(f"메시지 전송 실패: {connection_id}, 오류: {str(e)}")
        # 연결이 끊어진 경우 DynamoDB에서 제거
        if 'GoneException' in str(e):
            try:
                dynamodb_client.delete_item(
                    TableName=CONNECTIONS_TABLE,
                    Key={'connectionId': {'S': connection_id}}
                )
            except:
                pass

def send_error(connection_id, error_message):
    """
    오류 메시지 전송
    """
    send_message(connection_id, {
        "type": "error",
        "message": error_message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        'statusCode': 400,
        'body': json.dumps({'error': error_message})
    }