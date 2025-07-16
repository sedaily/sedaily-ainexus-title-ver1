"""
단순한 프롬프트 카드 저장/관리 Lambda 함수
- FAISS 복잡성 제거
- 6단계 워크플로우 하드코딩 제거
- 사용자 정의 프롬프트 카드 지원
- S3 + DynamoDB 기반 단순 저장
"""

import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal
import hashlib

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
PROMPT_BUCKET = os.environ['PROMPT_BUCKET']
REGION = os.environ['REGION']

class SimplePromptManager:
    """단순하고 효율적인 프롬프트 카드 관리"""
    
    def __init__(self):
        self.dynamodb_table = dynamodb.Table(PROMPT_META_TABLE)
    
    def create_prompt_card(self, project_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """새로운 프롬프트 카드 생성"""
        try:
            # 고유 ID 생성
            prompt_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # 사용자 입력 데이터 추출
            title = card_data.get('title', '').strip()
            # prompt_text 또는 content 필드 둘 다 지원
            content = card_data.get('prompt_text', card_data.get('content', '')).strip()
            step_order = card_data.get('stepOrder', 0)
            
            # 유효성 검사 - 내용만 필수
            if not content:
                return {'success': False, 'error': '내용이 필요합니다.'}
            
            # 제목이 없으면 기본 제목 생성
            if not title:
                title = f"프롬프트 {prompt_id[:8]}"
            
            # S3에 프롬프트 내용 저장
            s3_key = f"prompts/{project_id}/{prompt_id}/content.txt"
            
            try:
                s3_client.put_object(
                    Bucket=PROMPT_BUCKET,
                    Key=s3_key,
                    Body=content.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'project-id': project_id,
                        'prompt-id': prompt_id,
                        'created-at': timestamp
                    }
                )
                logger.info(f"S3에 프롬프트 내용 저장 완료: {s3_key}")
                
            except Exception as e:
                logger.error(f"S3 저장 실패: {str(e)}")
                return {'success': False, 'error': f'내용 저장 실패: {str(e)}'}
            
            # DynamoDB에 메타데이터 저장
            try:
                item = {
                    'projectId': project_id,
                    'promptId': prompt_id,
                    'title': title,
                    'stepOrder': int(step_order),
                    'isActive': True,
                    'createdAt': timestamp,
                    'updatedAt': timestamp,
                    's3Key': s3_key,
                    'contentLength': len(content),
                    'checksum': hashlib.md5(content.encode('utf-8')).hexdigest()
                }
                
                self.dynamodb_table.put_item(Item=item)
                logger.info(f"DynamoDB에 메타데이터 저장 완료: {prompt_id}")
                
                return {
                    'success': True,
                    'promptId': prompt_id,
                    'title': title,
                    'stepOrder': step_order,
                    'contentLength': len(content),
                    'createdAt': timestamp
                }
                
            except Exception as e:
                logger.error(f"DynamoDB 저장 실패: {str(e)}")
                # S3에서도 삭제 시도
                try:
                    s3_client.delete_object(Bucket=PROMPT_BUCKET, Key=s3_key)
                except:
                    pass
                return {'success': False, 'error': f'메타데이터 저장 실패: {str(e)}'}
                
        except Exception as e:
            logger.error(f"프롬프트 카드 생성 실패: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_prompt_card(self, project_id: str, prompt_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """기존 프롬프트 카드 업데이트"""
        try:
            # 기존 카드 조회
            try:
                response = self.dynamodb_table.get_item(
                    Key={'projectId': project_id, 'promptId': prompt_id}
                )
                if 'Item' not in response:
                    return {'success': False, 'error': '프롬프트 카드를 찾을 수 없습니다.'}
                
                existing_item = response['Item']
                
            except Exception as e:
                logger.error(f"기존 카드 조회 실패: {str(e)}")
                return {'success': False, 'error': '기존 카드 조회 실패'}
            
            # 업데이트할 데이터 준비
            title = card_data.get('title', existing_item.get('title', '')).strip()
            # prompt_text 또는 content 필드 둘 다 지원
            content = card_data.get('prompt_text', card_data.get('content', '')).strip()
            step_order = card_data.get('stepOrder', existing_item.get('stepOrder', 0))
            is_active = card_data.get('isActive', existing_item.get('isActive', True))
            
            # 제목이 없으면 기본 제목 생성
            if not title:
                title = f"프롬프트 {prompt_id[:8]}"
            
            timestamp = datetime.utcnow().isoformat()
            
            # 내용이 변경된 경우 S3 업데이트
            if content and content != existing_item.get('content', ''):
                s3_key = existing_item.get('s3Key', f"prompts/{project_id}/{prompt_id}/content.txt")
                
                try:
                    s3_client.put_object(
                        Bucket=PROMPT_BUCKET,
                        Key=s3_key,
                        Body=content.encode('utf-8'),
                        ContentType='text/plain',
                        Metadata={
                            'project-id': project_id,
                            'prompt-id': prompt_id,
                            'updated-at': timestamp
                        }
                    )
                    logger.info(f"S3 내용 업데이트 완료: {s3_key}")
                    
                except Exception as e:
                    logger.error(f"S3 업데이트 실패: {str(e)}")
                    return {'success': False, 'error': f'내용 업데이트 실패: {str(e)}'}
            else:
                # 내용이 변경되지 않은 경우 기존 값 사용
                s3_key = existing_item.get('s3Key')
                if content:
                    content_length = len(content)
                    checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
                else:
                    content_length = existing_item.get('contentLength', 0)
                    checksum = existing_item.get('checksum', '')
            
            # DynamoDB 업데이트
            try:
                update_expression = "SET title = :title, stepOrder = :step, isActive = :active, updatedAt = :updated"
                expression_values = {
                    ':title': title,
                    ':step': int(step_order),
                    ':active': is_active,
                    ':updated': timestamp
                }
                
                if content:
                    update_expression += ", contentLength = :length, checksum = :checksum"
                    expression_values[':length'] = len(content)
                    expression_values[':checksum'] = hashlib.md5(content.encode('utf-8')).hexdigest()
                
                self.dynamodb_table.update_item(
                    Key={'projectId': project_id, 'promptId': prompt_id},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values
                )
                
                logger.info(f"프롬프트 카드 업데이트 완료: {prompt_id}")
                
                return {
                    'success': True,
                    'promptId': prompt_id,
                    'title': title,
                    'stepOrder': step_order,
                    'isActive': is_active,
                    'updatedAt': timestamp
                }
                
            except Exception as e:
                logger.error(f"DynamoDB 업데이트 실패: {str(e)}")
                return {'success': False, 'error': f'업데이트 실패: {str(e)}'}
                
        except Exception as e:
            logger.error(f"프롬프트 카드 업데이트 실패: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_prompt_card(self, project_id: str, prompt_id: str) -> Dict[str, Any]:
        """프롬프트 카드 삭제"""
        try:
            # 기존 카드 조회
            try:
                response = self.dynamodb_table.get_item(
                    Key={'projectId': project_id, 'promptId': prompt_id}
                )
                if 'Item' not in response:
                    return {'success': False, 'error': '프롬프트 카드를 찾을 수 없습니다.'}
                
                existing_item = response['Item']
                s3_key = existing_item.get('s3Key')
                
            except Exception as e:
                logger.error(f"기존 카드 조회 실패: {str(e)}")
                return {'success': False, 'error': '기존 카드 조회 실패'}
            
            # S3에서 내용 삭제
            if s3_key:
                try:
                    s3_client.delete_object(Bucket=PROMPT_BUCKET, Key=s3_key)
                    logger.info(f"S3에서 프롬프트 내용 삭제 완료: {s3_key}")
                except Exception as e:
                    logger.warning(f"S3 삭제 실패: {str(e)}")
            
            # DynamoDB에서 메타데이터 삭제
            try:
                self.dynamodb_table.delete_item(
                    Key={'projectId': project_id, 'promptId': prompt_id}
                )
                logger.info(f"DynamoDB에서 메타데이터 삭제 완료: {prompt_id}")
                
                return {
                    'success': True,
                    'promptId': prompt_id,
                    'deletedAt': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"DynamoDB 삭제 실패: {str(e)}")
                return {'success': False, 'error': f'삭제 실패: {str(e)}'}
                
        except Exception as e:
            logger.error(f"프롬프트 카드 삭제 실패: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def load_project_prompts(self, project_id: str, include_content: bool = False) -> List[Dict[str, Any]]:
        """프로젝트의 모든 프롬프트 카드 로드"""
        try:
            # DynamoDB에서 프로젝트의 모든 프롬프트 카드 조회
            response = self.dynamodb_table.query(
                KeyConditionExpression='projectId = :pid',
                ExpressionAttributeValues={':pid': project_id},
                IndexName='projectId-stepOrder-index'  # GSI 사용
            )
            
            prompts = []
            for item in response.get('Items', []):
                prompt_data = {
                    'promptId': item['promptId'],
                    'title': item['title'],
                    'stepOrder': int(item['stepOrder']),
                    'isActive': item.get('isActive', True),
                    'createdAt': item['createdAt'],
                    'updatedAt': item['updatedAt'],
                    'contentLength': item.get('contentLength', 0),
                    'checksum': item.get('checksum', '')
                }
                
                # 내용 포함 요청 시 S3에서 내용 로드
                if include_content and item.get('s3Key'):
                    try:
                        s3_response = s3_client.get_object(
                            Bucket=PROMPT_BUCKET,
                            Key=item['s3Key']
                        )
                        prompt_data['content'] = s3_response['Body'].read().decode('utf-8')
                    except Exception as e:
                        logger.warning(f"S3 내용 로드 실패: {str(e)}")
                        prompt_data['content'] = ''
                
                prompts.append(prompt_data)
            
            # stepOrder로 정렬
            prompts.sort(key=lambda x: x['stepOrder'])
            
            logger.info(f"프로젝트 {project_id}의 프롬프트 카드 {len(prompts)}개 로드 완료")
            return prompts
            
        except Exception as e:
            logger.error(f"프롬프트 카드 로드 실패: {str(e)}")
            return []
    
    def get_project_prompt_stats(self, project_id: str) -> Dict[str, Any]:
        """프로젝트 프롬프트 통계 조회"""
        try:
            prompts = self.load_project_prompts(project_id)
            
            total_count = len(prompts)
            active_count = sum(1 for p in prompts if p.get('isActive', True))
            total_content_length = sum(p.get('contentLength', 0) for p in prompts)
            
            return {
                'totalCount': total_count,
                'activeCount': active_count,
                'inactiveCount': total_count - active_count,
                'totalContentLength': total_content_length,
                'averageContentLength': total_content_length / total_count if total_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"프롬프트 통계 조회 실패: {str(e)}")
            return {
                'totalCount': 0,
                'activeCount': 0,
                'inactiveCount': 0,
                'totalContentLength': 0,
                'averageContentLength': 0
            }

# 글로벌 인스턴스
prompt_manager = SimplePromptManager()

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """메인 핸들러 - 단순화된 프롬프트 관리"""
    
    try:
        logger.info(f"프롬프트 관리 요청 수신: {json.dumps(event, ensure_ascii=False)}")
        
        http_method = event.get('httpMethod', 'POST')
        
        # CORS 처리
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # 요청 본문 파싱 개선
        body = {}
        if event.get('body'):
            try:
                if isinstance(event['body'], str):
                    body = json.loads(event['body'])
                else:
                    body = event['body']
                logger.info(f"파싱된 요청 본문: {json.dumps(body, ensure_ascii=False)}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {str(e)}")
                return create_error_response(400, f'잘못된 JSON 형식: {str(e)}')
        
        path_params = event.get('pathParameters', {}) or {}
        project_id = path_params.get('projectId')
        
        if not project_id:
            return create_error_response(400, '프로젝트 ID가 필요합니다.')
        
        logger.info(f"프로젝트 ID: {project_id}, 메서드: {http_method}")
        
        # 메서드별 처리
        if http_method == 'GET':
            # 프롬프트 카드 목록 조회
            query_params = event.get('queryStringParameters') or {}
            include_content = query_params.get('includeContent', 'false').lower() == 'true'
            include_stats = query_params.get('includeStats', 'false').lower() == 'true'
            
            prompt_id = path_params.get('promptId')
            if prompt_id:
                # 개별 프롬프트 카드 조회
                prompts = prompt_manager.load_project_prompts(project_id)
                prompt_card = next((p for p in prompts if p['promptId'] == prompt_id), None)
                
                if not prompt_card:
                    return create_error_response(404, '프롬프트 카드를 찾을 수 없습니다.')
                
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'promptCard': prompt_card
                    }, ensure_ascii=False)
                }
            else:
                # 프로젝트의 모든 프롬프트 카드 목록 조회
                prompts = prompt_manager.load_project_prompts(project_id)
                
                response_data = {
                    'promptCards': prompts,
                    'count': len(prompts)
                }
                
                if include_stats:
                    stats = prompt_manager.get_project_prompt_stats(project_id)
                    response_data['stats'] = stats
                
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps(response_data, ensure_ascii=False)
                }
                
        elif http_method == 'POST':
            # 새 프롬프트 카드 생성
            result = prompt_manager.create_prompt_card(project_id, body)
            
            if result['success']:
                return {
                    'statusCode': 201,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': '프롬프트 카드가 생성되었습니다.',
                        'promptCard': result
                    }, ensure_ascii=False)
                }
            else:
                return create_error_response(400, result['error'])
        
        elif http_method == 'PUT':
            # 기존 프롬프트 카드 업데이트
            prompt_id = path_params.get('promptId')
            if not prompt_id:
                return create_error_response(400, '프롬프트 ID가 필요합니다.')
            
            result = prompt_manager.update_prompt_card(project_id, prompt_id, body)
            
            if result['success']:
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': '프롬프트 카드가 업데이트되었습니다.',
                        'promptCard': result
                    }, ensure_ascii=False)
                }
            else:
                return create_error_response(400, result['error'])
        
        elif http_method == 'DELETE':
            # 프롬프트 카드 삭제
            prompt_id = path_params.get('promptId')
            if not prompt_id:
                return create_error_response(400, '프롬프트 ID가 필요합니다.')
            
            result = prompt_manager.delete_prompt_card(project_id, prompt_id)
            
            if result['success']:
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': '프롬프트 카드가 삭제되었습니다.',
                        'deletedCard': result
                    }, ensure_ascii=False)
                }
            else:
                return create_error_response(400, result['error'])
        
        else:
            return create_error_response(405, '지원하지 않는 메서드입니다.')
            
    except Exception as e:
        logger.error(f"핸들러 오류: {str(e)}")
        return create_error_response(500, f'서버 오류: {str(e)}')

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '86400'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False)
    }