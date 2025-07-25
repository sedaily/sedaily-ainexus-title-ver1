import json
import boto3
import os
import logging
from typing import Dict, Any
from datetime import datetime

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
cognito_client = boto3.client('cognito-idp', region_name=os.environ['REGION'])
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])

# 환경 변수
USER_POOL_ID = os.environ['USER_POOL_ID']
CLIENT_ID = os.environ['USER_POOL_CLIENT_ID']
REGION = os.environ['REGION']
USERS_TABLE = os.environ.get('USERS_TABLE', '')

# DynamoDB 테이블
users_table = dynamodb.Table(USERS_TABLE) if USERS_TABLE else None

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    인증 관련 메인 핸들러
    
    지원하는 기능:
    - POST /auth/signup: 회원가입
    - POST /auth/signin: 로그인
    - POST /auth/refresh: 토큰 갱신
    - POST /auth/signout: 로그아웃
    - POST /auth/verify: 이메일 인증
    - POST /auth/forgot-password: 비밀번호 찾기
    - POST /auth/confirm-password: 비밀번호 재설정
    - POST /auth/init-admin: 관리자 계정 초기화 (내부 사용)
    """
    try:
        logger.info(f"인증 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event['httpMethod']
        path = event['path']
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # 라우팅
        if http_method == 'POST' and path == '/auth/signup':
            return signup(event)
        elif http_method == 'POST' and path == '/auth/signin':
            return signin(event)
        elif http_method == 'POST' and path == '/auth/refresh':
            return refresh_token(event)
        elif http_method == 'POST' and path == '/auth/signout':
            return signout(event)
        elif http_method == 'POST' and path == '/auth/verify':
            return verify_email(event)
        elif http_method == 'POST' and path == '/auth/forgot-password':
            return forgot_password(event)
        elif http_method == 'POST' and path == '/auth/confirm-password':
            return confirm_password(event)
        elif http_method == 'POST' and path == '/auth/init-admin':
            return init_admin_account(event)
        else:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': '요청한 경로를 찾을 수 없습니다'})
            }
            
    except Exception as e:
        logger.error(f"인증 처리 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '인증 처리 중 오류가 발생했습니다'})
        }

def init_admin_account(event: Dict[str, Any]) -> Dict[str, Any]:
    """관리자 계정 초기화"""
    try:
        admin_email = "ai@sedaily.com"
        admin_password = "Sedaily2024!"
        
        try:
            # 기존 관리자 계정 확인
            cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=admin_email
            )
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': '관리자 계정이 이미 존재합니다'})
            }
        except cognito_client.exceptions.UserNotFoundException:
            pass  # 계정이 없으므로 생성 진행
        
        # 관리자 계정 생성
        response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=admin_email,
            UserAttributes=[
                {'Name': 'email', 'Value': admin_email},
                {'Name': 'name', 'Value': '관리자'},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            TemporaryPassword=admin_password,
            MessageAction='SUPPRESS'  # 이메일 전송 억제
        )
        
        # 비밀번호를 영구적으로 설정
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=admin_email,
            Password=admin_password,
            Permanent=True
        )
        
        # 관리자 그룹에 추가
        try:
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=admin_email,
                GroupName='admin'
            )
        except Exception as e:
            logger.warning(f"관리자 그룹 추가 실패: {str(e)}")
        
        logger.info("관리자 계정 생성 완료")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '관리자 계정이 생성되었습니다',
                'email': admin_email,
                'userSub': response['User']['Username']
            })
        }
        
    except Exception as e:
        logger.error(f"관리자 계정 생성 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '관리자 계정 생성 중 오류가 발생했습니다'})
        }

def signup(event: Dict[str, Any]) -> Dict[str, Any]:
    """회원가입"""
    try:
        body = json.loads(event['body'])
        email = body['email']
        password = body['password']
        fullname = body.get('fullname', '')
        
        # Cognito 회원가입
        response = cognito_client.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': fullname}
            ]
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '회원가입이 완료되었습니다. 이메일 인증을 진행해주세요.',
                'userSub': response['UserSub']
            })
        }
        
    except cognito_client.exceptions.UsernameExistsException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '이미 존재하는 이메일입니다'})
        }
    except cognito_client.exceptions.InvalidPasswordException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '비밀번호가 정책에 맞지 않습니다'})
        }
    except Exception as e:
        logger.error(f"회원가입 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '회원가입 중 오류가 발생했습니다'})
        }

def signin(event: Dict[str, Any]) -> Dict[str, Any]:
    """로그인"""
    try:
        body = json.loads(event['body'])
        email = body['email']
        password = body['password']
        
        # Cognito 로그인
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'accessToken': response['AuthenticationResult']['AccessToken'],
                'idToken': response['AuthenticationResult']['IdToken'],
                'refreshToken': response['AuthenticationResult']['RefreshToken'],
                'expiresIn': response['AuthenticationResult']['ExpiresIn']
            })
        }
        
    except cognito_client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '이메일 또는 비밀번호가 올바르지 않습니다'})
        }
    except cognito_client.exceptions.UserNotConfirmedException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '이메일 인증이 필요합니다'})
        }
    except Exception as e:
        logger.error(f"로그인 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '로그인 중 오류가 발생했습니다'})
        }

def refresh_token(event: Dict[str, Any]) -> Dict[str, Any]:
    """토큰 갱신"""
    try:
        body = json.loads(event['body'])
        refresh_token = body['refreshToken']
        
        response = cognito_client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'accessToken': response['AuthenticationResult']['AccessToken'],
                'idToken': response['AuthenticationResult']['IdToken'],
                'expiresIn': response['AuthenticationResult']['ExpiresIn']
            })
        }
        
    except Exception as e:
        logger.error(f"토큰 갱신 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '토큰 갱신 중 오류가 발생했습니다'})
        }

def signout(event: Dict[str, Any]) -> Dict[str, Any]:
    """로그아웃"""
    try:
        headers = event.get('headers', {})
        access_token = headers.get('Authorization', '').replace('Bearer ', '')
        
        if access_token:
            cognito_client.global_sign_out(
                AccessToken=access_token
            )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '로그아웃되었습니다'})
        }
        
    except Exception as e:
        logger.error(f"로그아웃 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '로그아웃 중 오류가 발생했습니다'})
        }

def verify_email(event: Dict[str, Any]) -> Dict[str, Any]:
    """이메일 인증"""
    try:
        body = json.loads(event['body'])
        email = body['email']
        code = body['code']
        
        cognito_client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '이메일 인증이 완료되었습니다'})
        }
        
    except cognito_client.exceptions.CodeMismatchException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '인증 코드가 올바르지 않습니다'})
        }
    except Exception as e:
        logger.error(f"이메일 인증 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '이메일 인증 중 오류가 발생했습니다'})
        }

def forgot_password(event: Dict[str, Any]) -> Dict[str, Any]:
    """비밀번호 찾기"""
    try:
        body = json.loads(event['body'])
        email = body['email']
        
        cognito_client.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '비밀번호 재설정 코드가 이메일로 전송되었습니다'})
        }
        
    except Exception as e:
        logger.error(f"비밀번호 찾기 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '비밀번호 찾기 중 오류가 발생했습니다'})
        }

def confirm_password(event: Dict[str, Any]) -> Dict[str, Any]:
    """비밀번호 재설정"""
    try:
        body = json.loads(event['body'])
        email = body['email']
        code = body['code']
        new_password = body['newPassword']
        
        # Cognito에서 비밀번호 재설정
        cognito_client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code,
            Password=new_password
        )
        
        # 사용자 정보 가져오기
        try:
            user_info = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=email
            )
            user_sub = user_info['Username']
            
            # DynamoDB에 비밀번호 변경 이력 저장
            if users_table:
                # 기존 사용자 정보 업데이트 또는 새로 생성
                users_table.update_item(
                    Key={'userId': user_sub},
                    UpdateExpression='SET email = :email, lastPasswordChange = :timestamp, updatedAt = :timestamp',
                    ExpressionAttributeValues={
                        ':email': email,
                        ':timestamp': datetime.now().isoformat(),
                    },
                    ReturnValues='UPDATED_NEW'
                )
                logger.info(f"비밀번호 변경 이력이 사용자 {email}에 대해 저장되었습니다")
            
        except Exception as db_error:
            logger.warning(f"DynamoDB 업데이트 실패 (비밀번호는 성공적으로 변경됨): {str(db_error)}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '비밀번호가 재설정되었습니다'})
        }
        
    except cognito_client.exceptions.CodeMismatchException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '인증 코드가 올바르지 않습니다'})
        }
    except cognito_client.exceptions.ExpiredCodeException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '인증 코드가 만료되었습니다'})
        }
    except cognito_client.exceptions.InvalidPasswordException:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '비밀번호가 정책에 맞지 않습니다'})
        }
    except Exception as e:
        logger.error(f"비밀번호 재설정 중 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': '비밀번호 재설정 중 오류가 발생했습니다'})
        }

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }