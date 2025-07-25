"""
WebSocket 연결 처리 Lambda 함수
"""
import json
import os
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.client('dynamodb')
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE')

def handler(event, context):
    """
    WebSocket 연결 시 호출되는 함수
    """
    try:
        # 상세한 이벤트 로깅
        print(f"WebSocket 연결 이벤트: {json.dumps(event, indent=2)}")
        
        connection_id = event['requestContext']['connectionId']
        domain_name = event['requestContext']['domainName']
        stage = event['requestContext']['stage']
        
        print(f"연결 정보 - ID: {connection_id}, Domain: {domain_name}, Stage: {stage}")
        
        # 연결 정보를 DynamoDB에 저장 (TTL 1시간)
        ttl = int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        
        dynamodb.put_item(
            TableName=CONNECTIONS_TABLE,
            Item={
                'connectionId': {'S': connection_id},
                'connectedAt': {'S': datetime.utcnow().isoformat()},
                'domainName': {'S': domain_name},
                'stage': {'S': stage},
                'ttl': {'N': str(ttl)}
            }
        )
        
        print(f"WebSocket 연결 성공: {connection_id}")
        
        # WebSocket 연결에서는 body가 필요하지 않음
        return {
            'statusCode': 200
        }
        
    except Exception as e:
        print(f"연결 처리 오류: {str(e)}")
        print(f"오류 상세: {repr(e)}")
        
        # 연결 실패 시에도 적절한 응답 반환
        return {
            'statusCode': 500
        }