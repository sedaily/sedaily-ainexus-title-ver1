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
from pathlib import Path

# auth_utils 경로 추가
sys.path.append(str(Path(__file__).parent.parent / 'auth'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

try:
    from auth_utils import extract_user_from_event, get_cors_headers
    from common_utils import DecimalEncoder
except ImportError:
    # auth_utils가 없는 경우 기본 구현
    def extract_user_from_event(event):
        return {'user_id': 'default', 'email': 'default@example.com'}
    
    def get_cors_headers():
        return {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
            'Access-Control-Max-Age': '86400'
        }
    
    # DecimalEncoder fallback
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                if obj % 1 == 0:
                    return int(obj)
                else:
                    return float(obj)
            return super(DecimalEncoder, self).default(obj)

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

# 🔧 추가: 카테고리 관리를 위한 DynamoDB 테이블
CATEGORY_TABLE = os.environ.get('CATEGORY_TABLE', PROJECT_TABLE)  # 같은 테이블 사용 또는 별도 테이블

# =============================================================================
# 카테고리 관리 함수들
# =============================================================================

def list_categories(event: Dict[str, Any]) -> Dict[str, Any]:
    """사용자 카테고리 목록 조회"""
    try:
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 카테고리 데이터 조회 (partition key를 다르게 사용)
        response = table.scan(
            FilterExpression='#pk = :pk AND #sk BEGINS_WITH :sk_prefix',
            ExpressionAttributeNames={
                '#pk': 'ownerId',
                '#sk': 'projectId'
            },
            ExpressionAttributeValues={
                ':pk': user_id,
                ':sk_prefix': 'category#'
            }
        )
        
        categories = []
        for item in response.get('Items', []):
            # category# 접두사 제거
            category_id = item['projectId'].replace('category#', '')
            categories.append({
                'id': category_id,
                'name': item.get('name', ''),
                'description': item.get('description', ''),
                'color': item.get('color', 'gray'),
                'icon': item.get('icon', '🔧'),
                'createdAt': item.get('createdAt', ''),
                'updatedAt': item.get('updatedAt', '')
            })
        
        # 기본 카테고리가 없는 경우 생성
        if not categories:
            default_categories = [
                {'id': 'general', 'name': '일반', 'description': '일반적인 프로젝트', 'color': 'gray', 'icon': '🔧'},
                {'id': 'creative', 'name': '창작', 'description': '창의적인 컨텐츠', 'color': 'purple', 'icon': '✨'},
                {'id': 'analysis', 'name': '분석', 'description': '데이터 분석', 'color': 'blue', 'icon': '📊'},
                {'id': 'business', 'name': '비즈니스', 'description': '비즈니스 문서', 'color': 'green', 'icon': '💼'},
                {'id': 'education', 'name': '교육', 'description': '학습 자료', 'color': 'orange', 'icon': '📚'}
            ]
            
            # 기본 카테고리들을 DB에 저장
            for category in default_categories:
                table.put_item(Item={
                    'ownerId': user_id,
                    'projectId': f"category#{category['id']}",
                    'name': category['name'],
                    'description': category['description'],
                    'color': category['color'],
                    'icon': category['icon'],
                    'createdAt': datetime.utcnow().isoformat(),
                    'updatedAt': datetime.utcnow().isoformat(),
                    'status': 'active'
                })
            
            categories = default_categories
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'categories': categories,
                'count': len(categories),
                'message': '카테고리 목록을 성공적으로 조회했습니다.'
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"카테고리 목록 조회 실패: {str(e)}")

def create_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """새 카테고리 생성"""
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        category_name = body.get('name', '').strip()
        
        if not category_name:
            return create_error_response(400, "카테고리 이름이 필요합니다")
        
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        # 카테고리 ID 생성
        category_id = str(uuid.uuid4())
        
        # 카테고리 데이터 구성
        category_data = {
            'ownerId': user_id,
            'projectId': f"category#{category_id}",
            'name': category_name,
            'description': body.get('description', ''),
            'color': body.get('color', 'gray'),
            'icon': body.get('icon', '🔧'),
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        # DynamoDB에 저장
        table = dynamodb.Table(PROJECT_TABLE)
        table.put_item(Item=category_data)
        
        logger.info(f"새 카테고리 생성: {category_id} - {category_name}")
        
        # 응답용 데이터 (category# 접두사 제거)
        response_category = {
            'id': category_id,
            'name': category_name,
            'description': category_data['description'],
            'color': category_data['color'],
            'icon': category_data['icon'],
            'createdAt': category_data['createdAt'],
            'updatedAt': category_data['updatedAt']
        }
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(response_category, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 생성 실패: {str(e)}")
        return create_error_response(500, f"카테고리 생성 실패: {str(e)}")

def update_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """카테고리 수정"""
    try:
        category_id = event['pathParameters']['categoryId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 기존 카테고리 확인
        response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        if 'Item' not in response:
            return create_error_response(404, "카테고리를 찾을 수 없습니다")
        
        # 업데이트할 필드들
        update_expression = "SET #updatedAt = :updatedAt"
        expression_attribute_names = {'#updatedAt': 'updatedAt'}
        expression_attribute_values = {':updatedAt': datetime.utcnow().isoformat()}
        
        if 'name' in body:
            update_expression += ", #name = :name"
            expression_attribute_names['#name'] = 'name'
            expression_attribute_values[':name'] = body['name']
        
        if 'description' in body:
            update_expression += ", #description = :description"
            expression_attribute_names['#description'] = 'description'
            expression_attribute_values[':description'] = body['description']
        
        if 'color' in body:
            update_expression += ", #color = :color"
            expression_attribute_names['#color'] = 'color'
            expression_attribute_values[':color'] = body['color']
        
        if 'icon' in body:
            update_expression += ", #icon = :icon"
            expression_attribute_names['#icon'] = 'icon'
            expression_attribute_values[':icon'] = body['icon']
        
        # 업데이트 실행
        table.update_item(
            Key={
                'ownerId': user_id,
                'projectId': f"category#{category_id}"
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # 업데이트된 카테고리 조회
        updated_response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        updated_category = {
            'id': category_id,
            'name': updated_response['Item']['name'],
            'description': updated_response['Item'].get('description', ''),
            'color': updated_response['Item'].get('color', 'gray'),
            'icon': updated_response['Item'].get('icon', '🔧'),
            'createdAt': updated_response['Item'].get('createdAt', ''),
            'updatedAt': updated_response['Item']['updatedAt']
        }
        
        logger.info(f"카테고리 수정: {category_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(updated_category, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 수정 실패: {str(e)}")
        return create_error_response(500, f"카테고리 수정 실패: {str(e)}")

def delete_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """카테고리 삭제"""
    try:
        category_id = event['pathParameters']['categoryId']
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 기존 카테고리 확인
        response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        if 'Item' not in response:
            return create_error_response(404, "카테고리를 찾을 수 없습니다")
        
        # 해당 카테고리를 사용하는 프로젝트가 있는지 확인
        projects_response = table.scan(
            FilterExpression='#ownerId = :ownerId AND #category = :category AND NOT begins_with(#projectId, :category_prefix)',
            ExpressionAttributeNames={
                '#ownerId': 'ownerId',
                '#category': 'category',
                '#projectId': 'projectId'
            },
            ExpressionAttributeValues={
                ':ownerId': user_id,
                ':category': category_id,
                ':category_prefix': 'category#'
            }
        )
        
        if projects_response.get('Items'):
            return create_error_response(400, "이 카테고리를 사용하는 프로젝트가 있어 삭제할 수 없습니다")
        
        # 카테고리 삭제
        table.delete_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        logger.info(f"카테고리 삭제: {category_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '카테고리가 삭제되었습니다',
                'categoryId': category_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"카테고리 삭제 실패: {str(e)}")
        return create_error_response(500, f"카테고리 삭제 실패: {str(e)}")

# =============================================================================
# 기존 프로젝트 관리 함수들
# =============================================================================

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    프로젝트 및 카테고리 관리 메인 핸들러
    
    Routes:
    - POST /projects: 새 프로젝트 생성
    - GET /projects: 프로젝트 목록 조회
    - GET /projects/{id}: 프로젝트 상세 조회
    - GET /projects/{id}/upload-url: 파일 업로드용 pre-signed URL 생성
    - GET /categories: 사용자 카테고리 목록 조회
    - POST /categories: 새 카테고리 생성
    - PUT /categories/{id}: 카테고리 수정
    - DELETE /categories/{id}: 카테고리 삭제
    """
    try:
        logger.info(f"프로젝트/카테고리 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        resource = event.get('resource', '')
        path_parameters = event.get('pathParameters', {}) or {}
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # 카테고리 관련 라우팅
        if '/categories' in path or '/categories' in resource:
            if path_parameters.get('categoryId'):
                # 개별 카테고리 작업
                if http_method == 'PUT':
                    return update_category(event)
                elif http_method == 'DELETE':
                    return delete_category(event)
                else:
                    return create_error_response(405, "지원하지 않는 메소드입니다")
            else:
                # 카테고리 목록 작업
                if http_method == 'GET':
                    return list_categories(event)
                elif http_method == 'POST':
                    return create_category(event)
                else:
                    return create_error_response(405, "지원하지 않는 메소드입니다")
        
        # 기존 프로젝트 관련 라우팅
        elif 'upload-url' in resource:
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
        logger.error(f"프로젝트/카테고리 처리 중 오류 발생: {str(e)}")
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