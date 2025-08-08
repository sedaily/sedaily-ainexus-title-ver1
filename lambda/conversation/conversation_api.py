import json
import boto3
import os
from datetime import datetime
import uuid

def handler(event, context):
    """대화 관리 API"""
    
    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        
        # OPTIONS 요청 처리 (CORS preflight)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': ''
            }
        
        # GET /conversations - 대화 목록 조회
        if http_method == 'GET' and path == '/conversations':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'conversations': [],
                    'total': 0,
                    'message': 'No conversations found'
                })
            }
        
        # POST /conversations - 새 대화 생성
        elif http_method == 'POST' and path == '/conversations':
            conversation_id = str(uuid.uuid4())
            return {
                'statusCode': 201,
                'headers': headers,
                'body': json.dumps({
                    'conversation_id': conversation_id,
                    'title': 'New Conversation',
                    'created_at': datetime.utcnow().isoformat()
                })
            }
        
        # 기타 경로
        else:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'message': 'Conversation API working',
                    'method': http_method,
                    'path': path
                })
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }
EOF < /dev/null