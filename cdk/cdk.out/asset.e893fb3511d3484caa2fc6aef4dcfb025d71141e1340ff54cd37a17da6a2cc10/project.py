import json
import boto3
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import urllib.parse
import sys
from decimal import Decimal

# 인증 유틸리티 임포트를 위한 경로 추가
sys.path.append('/opt/python')  # Lambda Layer 경로
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../auth')

try:
    from auth_utils import extract_user_from_event, get_cors_headers
except ImportError:
    # auth_utils가 없는 경우 기본 구현
    def extract_user_from_event(event):
        return {'user_id': 'default', 'email': 'default@example.com'}
    
    def get_cors_headers():
        return {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
        }

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
PROJECT_TABLE = os.environ['PROJECT_TABLE']
PROMPT_BUCKET = os.environ['PROMPT_BUCKET']
REGION = os.environ['REGION']

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON 직렬화 가능한 타입으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Decimal을 float 또는 int로 변환
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    프로젝트 관리 메인 핸들러
    
    Routes:
    - POST /projects: 새 프로젝트 생성
    - GET /projects: 프로젝트 목록 조회
    - GET /projects/{id}: 프로젝트 상세 조회
    - GET /projects/{id}/upload-url: 파일 업로드용 pre-signed URL 생성
    """
    try:
        logger.info(f"프로젝트 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'GET')
        path_parameters = event.get('pathParameters', {}) or {}
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # 경로별 라우팅
        if 'upload-url' in event.get('resource', ''):
            return get_upload_url(event)
        elif path_parameters.get('projectId'):
            return get_project(event)
        elif http_method == 'POST':
            return create_project(event)
        elif http_method == 'GET':
            return list_projects(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"프로젝트 처리 중 오류 발생: {str(e)}")
        # 예외 발생 시에도 CORS 헤더 포함
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': f"내부 서버 오류: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }

def create_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """새 프로젝트 생성"""
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        project_name = body.get('name', '').strip()
        
        if not project_name:
            return create_error_response(400, "프로젝트 이름이 필요합니다")
        
        # 프로젝트 ID 생성
        project_id = str(uuid.uuid4())
        
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        user_email = user.get('email', 'unknown')
        
        # 프로젝트 데이터 구성
        project_data = {
            'projectId': project_id,
            'name': project_name,
            'description': body.get('description', ''),
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'promptCount': 0,
            'conversationCount': 0,
            'tags': body.get('tags', []),
            'ownerId': user_id,  # 프로젝트 소유자 ID
            'ownerEmail': user_email,  # 프로젝트 소유자 이메일
            # AI 커스터마이징 필드들
            'aiRole': body.get('aiRole', ''),
            'aiInstructions': body.get('aiInstructions', ''),
            'targetAudience': body.get('targetAudience', '일반독자'),
            'outputFormat': body.get('outputFormat', 'multiple'),
            'styleGuidelines': body.get('styleGuidelines', '')
        }
        
        # DynamoDB에 저장
        table = dynamodb.Table(PROJECT_TABLE)
        table.put_item(Item=project_data)
        
        logger.info(f"새 프로젝트 생성: {project_id} - {project_name}")
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(project_data, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 생성 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 생성 실패: {str(e)}")

def list_projects(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 목록 조회 (사용자별 필터링)"""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        # 페이지네이션 파라미터
        limit = int(query_params.get('limit', 20))
        last_evaluated_key = query_params.get('lastKey')
        
        # 상태 필터
        status_filter = query_params.get('status', 'active')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 스캔 파라미터 구성 (사용자별 필터링 추가)
        scan_params = {
            'Limit': limit,
            'FilterExpression': '#status = :status AND #ownerId = :ownerId',
            'ExpressionAttributeNames': {
                '#status': 'status',
                '#ownerId': 'ownerId'
            },
            'ExpressionAttributeValues': {
                ':status': status_filter,
                ':ownerId': user_id
            }
        }
        
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = {'projectId': last_evaluated_key}
        
        response = table.scan(**scan_params)
        
        # 결과 정렬 (최신순)
        projects = sorted(response['Items'], key=lambda x: x['createdAt'], reverse=True)
        
        result = {
            'projects': projects,
            'count': len(projects),
            'hasMore': 'LastEvaluatedKey' in response
        }
        
        if 'LastEvaluatedKey' in response:
            result['nextKey'] = response['LastEvaluatedKey']['projectId']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 목록 조회 실패: {str(e)}")

def get_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 상세 조회 (소유권 확인)"""
    try:
        project_id = event['pathParameters']['projectId']
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        response = table.get_item(Key={'projectId': project_id})
        
        if 'Item' not in response:
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        project = response['Item']
        
        # 소유권 확인
        if project.get('ownerId') != user_id:
            return create_error_response(403, "프로젝트에 접근할 권한이 없습니다")
        
        # 프롬프트 정보 추가 조회
        project['prompts'] = get_project_prompts(project_id)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(project, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 조회 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 조회 실패: {str(e)}")

def update_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 업데이트"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # 업데이트 가능한 필드들
        update_fields = ['name', 'description', 'tags', 'status', 'aiRole', 'aiInstructions', 'targetAudience', 'outputFormat', 'styleGuidelines']
        update_expression = "SET updatedAt = :updatedAt"
        expression_values = {':updatedAt': datetime.utcnow().isoformat()}
        
        for field in update_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f':{field}'] = body[field]
        
        table = dynamodb.Table(PROJECT_TABLE)
        response = table.update_item(
            Key={'projectId': project_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response['Attributes'], ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 업데이트 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 업데이트 실패: {str(e)}")

def delete_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 삭제"""
    try:
        project_id = event['pathParameters']['projectId']
        
        # 프로젝트 존재 확인
        table = dynamodb.Table(PROJECT_TABLE)
        response = table.get_item(Key={'projectId': project_id})
        
        if 'Item' not in response:
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        # 소프트 삭제 (상태를 'deleted'로 변경)
        table.update_item(
            Key={'projectId': project_id},
            UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'deleted',
                ':updatedAt': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"프로젝트 삭제: {project_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '프로젝트가 삭제되었습니다'}, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 삭제 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 삭제 실패: {str(e)}")

def get_upload_url(event: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 파일 업로드용 pre-signed URL 생성"""
    try:
        project_id = event['pathParameters']['projectId']
        query_params = event.get('queryStringParameters') or {}
        
        category = query_params.get('category', '')
        filename = query_params.get('filename', '')
        
        if not category or not filename:
            return create_error_response(400, "카테고리와 파일명이 필요합니다")
        
        # S3 키 생성: {projectId}/{category}/{filename}
        s3_key = f"{project_id}/{category}/{filename}"
        
        # Pre-signed URL 생성
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': PROMPT_BUCKET,
                'Key': s3_key,
                'ContentType': 'text/plain'
            },
            ExpiresIn=3600  # 1시간
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'uploadUrl': presigned_url,
                's3Key': s3_key,
                'bucket': PROMPT_BUCKET,
                'expiresIn': 3600
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"업로드 URL 생성 실패: {str(e)}")
        return create_error_response(500, f"업로드 URL 생성 실패: {str(e)}")

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 프롬프트 메타데이터 조회"""
    try:
        # 실제 구현에서는 PROMPT_META_TABLE을 사용
        # 현재는 간단하게 빈 리스트 반환
        return []
        
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        return []

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
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