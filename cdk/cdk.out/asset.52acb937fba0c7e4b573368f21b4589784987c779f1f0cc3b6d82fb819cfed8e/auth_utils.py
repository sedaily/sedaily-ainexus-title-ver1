import json
import base64
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger()

def extract_user_from_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    API Gateway Cognito Authorizer에서 사용자 정보 추출
    
    Args:
        event: Lambda 이벤트 객체
        
    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    try:
        # API Gateway Cognito Authorizer가 설정한 사용자 정보
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        
        # Cognito 사용자 정보
        claims = authorizer.get('claims', {})
        
        if claims:
            return {
                'user_id': claims.get('sub'),
                'email': claims.get('email'),
                'name': claims.get('name', ''),
                'email_verified': claims.get('email_verified') == 'true',
                'token_use': claims.get('token_use'),
                'iss': claims.get('iss'),
                'aud': claims.get('aud'),
                'exp': claims.get('exp'),
                'iat': claims.get('iat')
            }
            
        # 만약 직접 JWT 토큰을 파싱해야 하는 경우 (fallback)
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]  # 'Bearer ' 제거
            return parse_jwt_token(token)
            
        return None
        
    except Exception as e:
        logger.error(f"사용자 정보 추출 실패: {str(e)}")
        return None

def parse_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰을 파싱하여 사용자 정보 추출 (검증 없이 payload만 추출)
    
    Note: 이 함수는 API Gateway Cognito Authorizer가 이미 토큰을 검증했다고 가정합니다.
    실제 프로덕션에서는 토큰 서명 검증이 필요합니다.
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        사용자 정보 딕셔너리 또는 None
    """
    try:
        # JWT는 header.payload.signature로 구성됨
        parts = token.split('.')
        if len(parts) != 3:
            logger.error("잘못된 JWT 토큰 형식")
            return None
            
        # payload 부분 디코딩
        payload = parts[1]
        
        # Base64 패딩 추가 (필요한 경우)
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
            
        # Base64 디코딩 후 JSON 파싱
        decoded_payload = base64.b64decode(payload)
        claims = json.loads(decoded_payload)
        
        return {
            'user_id': claims.get('sub'),
            'email': claims.get('email'),
            'name': claims.get('name', ''),
            'email_verified': claims.get('email_verified'),
            'token_use': claims.get('token_use'),
            'iss': claims.get('iss'),
            'aud': claims.get('aud'),
            'exp': claims.get('exp'),
            'iat': claims.get('iat')
        }
        
    except Exception as e:
        logger.error(f"JWT 토큰 파싱 실패: {str(e)}")
        return None

def require_auth(func):
    """
    인증이 필요한 Lambda 함수를 위한 데코레이터
    
    Usage:
        @require_auth
        def handler(event, context):
            user = event.get('user')  # 사용자 정보 사용
            # ...
    """
    def wrapper(event, context):
        user = extract_user_from_event(event)
        
        if not user:
            return {
                'statusCode': 401,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
                },
                'body': json.dumps({'error': '인증이 필요합니다'})
            }
        
        # 이벤트에 사용자 정보 추가
        event['user'] = user
        
        return func(event, context)
    
    return wrapper

def get_user_id_from_event(event: Dict[str, Any]) -> Optional[str]:
    """
    이벤트에서 사용자 ID 추출 (간편 함수)
    
    Args:
        event: Lambda 이벤트 객체
        
    Returns:
        사용자 ID 문자열 또는 None
    """
    user = extract_user_from_event(event)
    return user.get('user_id') if user else None

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }