"""
대용량 문서 배치 처리 Lambda 함수
SQS에서 청크를 받아 AI 처리 후 결과를 WebSocket으로 전송
"""
import json
import os
import boto3
import traceback
from datetime import datetime

# AWS 클라이언트 초기화
bedrock_client = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION"))
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("REGION"))
apigateway_client = boto3.client("apigatewaymanagementapi")

# 환경 변수
BATCH_JOBS_TABLE = os.environ.get("BATCH_JOBS_TABLE")
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE")
REGION = os.environ.get("REGION")

def handler(event, context):
    """SQS 이벤트 처리"""
    try:
        for record in event['Records']:
            message_body = json.loads(record['body'])
            process_chunk(message_body)
        
        return {"statusCode": 200}
        
    except Exception as e:
        print(f"배치 처리 오류: {traceback.format_exc()}")
        return {"statusCode": 500, "body": str(e)}

def process_chunk(message):
    """개별 청크 처리"""
    try:
        job_id = message['job_id']
        chunk_id = message['chunk_id']
        content = message['content']
        prompt = message['prompt']
        connection_id = message.get('connection_id')
        
        print(f"청크 처리 시작: job_id={job_id}, chunk_id={chunk_id}")
        
        # 작업 상태 업데이트
        update_job_status(job_id, chunk_id, "processing")
        
        # AI 처리
        result = process_with_bedrock(content, prompt)
        
        # 결과 저장
        update_job_status(job_id, chunk_id, "completed", result)
        
        # WebSocket으로 실시간 결과 전송
        if connection_id:
            send_websocket_message(connection_id, {
                "type": "chunk_result",
                "job_id": job_id,
                "chunk_id": chunk_id,
                "result": result
            })
        
        print(f"청크 처리 완료: job_id={job_id}, chunk_id={chunk_id}")
        
    except Exception as e:
        print(f"청크 처리 오류: {e}")
        update_job_status(job_id, chunk_id, "failed", str(e))
        
        if connection_id:
            send_websocket_message(connection_id, {
                "type": "chunk_error",
                "job_id": job_id,
                "chunk_id": chunk_id,
                "error": str(e)
            })

def process_with_bedrock(content, prompt):
    """Bedrock으로 AI 처리"""
    try:
        final_prompt = f"{prompt}\n\n{content}"
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.1
        }
        
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except Exception as e:
        print(f"Bedrock 처리 오류: {e}")
        raise

def update_job_status(job_id, chunk_id, status, result=None):
    """작업 상태 업데이트"""
    try:
        table = dynamodb.Table(BATCH_JOBS_TABLE)
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if result:
            update_data["result"] = result
        
        table.update_item(
            Key={"job_id": f"{job_id}#{chunk_id}"},
            UpdateExpression="SET #status = :status, updated_at = :updated_at" + 
                           (", #result = :result" if result else ""),
            ExpressionAttributeNames={
                "#status": "status",
                **({"#result": "result"} if result else {})
            },
            ExpressionAttributeValues={
                ":status": status,
                ":updated_at": update_data["updated_at"],
                **({"result": result} if result else {})
            }
        )
        
    except Exception as e:
        print(f"상태 업데이트 오류: {e}")

def send_websocket_message(connection_id, message):
    """WebSocket으로 메시지 전송"""
    try:
        # WebSocket API 엔드포인트 설정 (환경에 따라 조정 필요)
        websocket_url = f"https://xov5aktydl.execute-api.{REGION}.amazonaws.com/prod"
        
        apigateway_client = boto3.client(
            "apigatewaymanagementapi",
            endpoint_url=websocket_url
        )
        
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        
    except Exception as e:
        print(f"WebSocket 전송 오류: {e}")