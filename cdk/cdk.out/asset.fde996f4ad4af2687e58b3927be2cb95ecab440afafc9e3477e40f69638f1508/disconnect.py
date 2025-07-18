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
        connection_id = event['requestContext']['connectionId']
        
        # 연결 정보를 DynamoDB에서 제거
        dynamodb.delete_item(
            TableName=CONNECTIONS_TABLE,
            Key={
                'connectionId': {'S': connection_id}
            }
        )
        
        print(f"WebSocket 연결 해제 성공: {connection_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': '연결 해제 성공'})
        }
        
    except Exception as e:
        print(f"연결 해제 처리 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }