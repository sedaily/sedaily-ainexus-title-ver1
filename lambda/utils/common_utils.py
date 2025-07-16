import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON 직렬화 가능한 타입으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False, cls=DecimalEncoder)
    }

def create_success_response(data: Any, status_code: int = 200) -> Dict[str, Any]:
    """성공 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps(data, ensure_ascii=False, cls=DecimalEncoder)
    }

def load_prompt_from_s3(s3_client, bucket: str, s3_key: str) -> str:
    """S3에서 프롬프트 텍스트 로드 (공통 함수)"""
    if not s3_key or not bucket:
        return ""
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.warning(f"S3에서 프롬프트 로드 실패: {s3_key}, {str(e)}")
        return ""

def get_aws_clients(region: str):
    """AWS 클라이언트들을 한번에 초기화"""
    return {
        'dynamodb': boto3.resource('dynamodb', region_name=region),
        's3': boto3.client('s3', region_name=region),
        'bedrock': boto3.client('bedrock-runtime', region_name=region),
    }

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> tuple:
    """필수 필드 검증"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"필수 필드가 누락되었습니다: {', '.join(missing_fields)}"
    
    return True, "" 