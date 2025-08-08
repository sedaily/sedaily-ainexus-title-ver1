import json
import boto3
import os
from datetime import datetime
import uuid

def handler(event, context):
    """메시지 관리 API"""
    
    # CORS 헤더
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
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
        
        # 메시지 관련 API
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Message API working',
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