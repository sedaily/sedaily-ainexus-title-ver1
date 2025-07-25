"""
WebSocket 연결 해제 처리 Lambda 함수
"""
import json
import os
import boto3

dynamodb = boto3.client('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE')

def handler(event, context):
    """
    WebSocket 연결 해제 시 호출되는 함수
    """
    try:
        # 상세한 이벤트 로깅
        print(f"WebSocket 연결 해제 이벤트: {json.dumps(event, indent=2)}")
        
        connection_id = event['requestContext']['connectionId']
        
        print(f"연결 해제 처리 중: {connection_id}")
        
        # 연결 정보를 DynamoDB에서 제거
        dynamodb.delete_item(
            TableName=CONNECTIONS_TABLE,
            Key={
                'connectionId': {'S': connection_id}
            }
        )
        
        print(f"WebSocket 연결 해제 성공: {connection_id}")
        
        # WebSocket 연결 해제에서는 body가 필요하지 않음
        return {
            'statusCode': 200
        }
        
    except Exception as e:
        print(f"연결 해제 처리 오류: {str(e)}")
        print(f"오류 상세: {repr(e)}")
        
        return {
            'statusCode': 500
        }