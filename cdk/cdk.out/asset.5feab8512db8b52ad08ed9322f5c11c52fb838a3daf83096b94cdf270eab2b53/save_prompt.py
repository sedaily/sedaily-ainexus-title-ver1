"""
단순한 프롬프트 카드 저장/관리 Lambda 함수
- FAISS 복잡성 제거
- 사용자 정의 프롬프트 카드 지원
- S3 + DynamoDB 기반 단순 저장
"""

import json
import boto3
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List
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

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON으로 변환하는 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

class SimplePromptManager:
    """단순하고 효율적인 프롬프트 카드 관리"""
    
    def __init__(self):
        self.dynamodb_table = dynamodb.Table(PROMPT_META_TABLE)
    
    def create_prompt_card(self, project_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            title = card_data.get('title', '').strip()
            content = card_data.get('prompt_text', card_data.get('content', '')).strip()
            tags = card_data.get('tags', [])  # 태그 필드 추가
            
            if len(tags) > 5:
                return {'success': False, 'error': '태그는 최대 5개까지 추가할 수 있습니다.'}

            if not content: return {'success': False, 'error': '내용이 필요합니다.'}
            if not title: title = f"프롬프트 {prompt_id[:8]}"
            
            s3_key = f"prompts/{project_id}/{prompt_id}/content.txt"
            
            try:
                s3_client.put_object(
                    Bucket=PROMPT_BUCKET, Key=s3_key, Body=content.encode('utf-8'),
                    ContentType='text/plain', Metadata={'project-id': project_id, 'prompt-id': prompt_id}
                )
            except Exception as e:
                return {'success': False, 'error': f'내용 저장 실패: {str(e)}'}
            
            item = {
                'projectId': project_id, 'promptId': prompt_id, 'title': title,
                'isActive': True, 'createdAt': timestamp, 'updatedAt': timestamp,
                's3Key': s3_key, 'contentLength': len(content),
                'checksum': hashlib.md5(content.encode('utf-8')).hexdigest(),
                'tags': tags  # 태그 필드 저장
            }
            self.dynamodb_table.put_item(Item=item)
            logger.info(f"프롬프트 카드 생성 성공 - promptId: {prompt_id}, title: {title}")
            return {'success': True, 'promptId': prompt_id, 'title': title, 'createdAt': timestamp}
        except Exception as e:
            logger.error(f"카드 생성 실패: {str(e)}")
            return {'success': False, 'error': str(e)}

    def update_prompt_card(self, project_id: str, prompt_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = self.dynamodb_table.get_item(Key={'projectId': project_id, 'promptId': prompt_id})
            if 'Item' not in response: return {'success': False, 'error': '프롬프트 카드를 찾을 수 없습니다.'}
            
            update_expression = "SET updatedAt = :updated"
            expression_values = {':updated': datetime.utcnow().isoformat()}

            if 'title' in card_data:
                update_expression += ", title = :title"
                expression_values[':title'] = card_data['title'].strip()
            if 'isActive' in card_data:
                update_expression += ", isActive = :active"
                expression_values[':active'] = card_data['isActive']
            if 'tags' in card_data:  # 태그 업데이트 처리 추가
                if len(card_data['tags']) > 5:
                    return {'success': False, 'error': '태그는 최대 5개까지 추가할 수 있습니다.'}
                update_expression += ", tags = :tags"
                expression_values[':tags'] = card_data['tags']
            
            # 프롬프트 내용 업데이트도 처리
            if 'prompt_text' in card_data or 'content' in card_data:
                content = card_data.get('prompt_text', card_data.get('content', '')).strip()
                if content:
                    # 기존 아이템에서 s3Key 가져오기
                    existing_item = response['Item']
                    s3_key = existing_item.get('s3Key')
                    
                    if not s3_key:
                        s3_key = f"prompts/{project_id}/{prompt_id}/content.txt"
                    
                    try:
                        s3_client.put_object(
                            Bucket=PROMPT_BUCKET, Key=s3_key, Body=content.encode('utf-8'),
                            ContentType='text/plain', Metadata={'project-id': project_id, 'prompt-id': prompt_id}
                        )
                        
                        # S3 업데이트 성공 시 메타데이터도 업데이트
                        update_expression += ", contentLength = :length, checksum = :checksum"
                        expression_values[':length'] = len(content)
                        expression_values[':checksum'] = hashlib.md5(content.encode('utf-8')).hexdigest()
                        
                        if not existing_item.get('s3Key'):
                            update_expression += ", s3Key = :s3key"
                            expression_values[':s3key'] = s3_key
                            
                    except Exception as e:
                        logger.error(f"S3 업데이트 실패: {str(e)}")
                        return {'success': False, 'error': f'내용 저장 실패: {str(e)}'}
            
            self.dynamodb_table.update_item(
                Key={'projectId': project_id, 'promptId': prompt_id},
                UpdateExpression=update_expression, ExpressionAttributeValues=expression_values
            )
            logger.info(f"프롬프트 카드 수정 성공 - promptId: {prompt_id}, 수정된 필드: {list(card_data.keys())}")
            return {'success': True, 'promptId': prompt_id}
        except Exception as e:
            logger.error(f"카드 업데이트 실패: {str(e)}")
            return {'success': False, 'error': str(e)}

    def delete_prompt_card(self, project_id: str, prompt_id: str) -> Dict[str, Any]:
        try:
            self.dynamodb_table.delete_item(Key={'projectId': project_id, 'promptId': prompt_id})
            logger.info(f"프롬프트 카드 삭제 성공 - promptId: {prompt_id}")
            return {'success': True, 'promptId': prompt_id}
        except Exception as e:
            logger.error(f"카드 삭제 실패: {str(e)}")
            return {'success': False, 'error': str(e)}

    def load_project_prompts(self, project_id: str, include_content: bool = False) -> List[Dict[str, Any]]:
        try:
            response = self.dynamodb_table.scan(FilterExpression='projectId = :pid', ExpressionAttributeValues={':pid': project_id})
            prompts = []
            for item in response.get('Items', []):
                clean_item = {k: (int(v) if isinstance(v, Decimal) else v) for k, v in item.items()}
                
                if include_content and clean_item.get('s3Key'):
                    s3_response = s3_client.get_object(Bucket=PROMPT_BUCKET, Key=clean_item['s3Key'])
                    clean_item['content'] = s3_response['Body'].read().decode('utf-8')
                prompts.append(clean_item)
            
            prompts.sort(key=lambda x: x.get('createdAt', ''))
            return prompts
        except Exception as e:
            logger.error(f"프롬프트 로드 실패: {str(e)}")
            return []

prompt_manager = SimplePromptManager()

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"핸들러 시작 - Method: {event.get('httpMethod')}, Path: {event.get('path')}")
    logger.info(f"Event: {json.dumps(event, ensure_ascii=False)[:500]}")  # 처음 500자만 로깅
    
    try:
        http_method = event.get('httpMethod', 'POST')
        if http_method == 'OPTIONS':
            logger.info("OPTIONS 요청 처리")
            return {'statusCode': 200, 'headers': get_cors_headers(), 'body': ''}
        
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        path_params = event.get('pathParameters', {}) or {}
        project_id = path_params.get('projectId')
        
        if not project_id:
            return create_error_response(400, '프로젝트 ID가 필요합니다.')
        
        response_data = {}
        status_code = 200

        if http_method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            include_content = query_params.get('includeContent', 'false').lower() == 'true'
            prompts = prompt_manager.load_project_prompts(project_id, include_content)
            response_data = {'promptCards': prompts, 'count': len(prompts)}
            
        elif http_method == 'POST':
            logger.info(f"POST 요청 - projectId: {project_id}, body: {json.dumps(body, ensure_ascii=False)[:200]}")
            response_data = prompt_manager.create_prompt_card(project_id, body)
            logger.info(f"프롬프트 생성 결과: {json.dumps(response_data, ensure_ascii=False)}")
            if response_data.get('success'):
                status_code = 201

        elif http_method == 'PUT':
            prompt_id = path_params.get('promptId')
            if not prompt_id: return create_error_response(400, '프롬프트 ID가 필요합니다.')
            logger.info(f"PUT 요청 - projectId: {project_id}, promptId: {prompt_id}, body: {json.dumps(body, ensure_ascii=False)[:200]}")
            response_data = prompt_manager.update_prompt_card(project_id, prompt_id, body)
            logger.info(f"프롬프트 수정 결과: {json.dumps(response_data, ensure_ascii=False)}")

        elif http_method == 'DELETE':
            prompt_id = path_params.get('promptId')
            if not prompt_id: return create_error_response(400, '프롬프트 ID가 필요합니다.')
            logger.info(f"DELETE 요청 - projectId: {project_id}, promptId: {prompt_id}")
            response_data = prompt_manager.delete_prompt_card(project_id, prompt_id)
            logger.info(f"프롬프트 삭제 결과: {json.dumps(response_data, ensure_ascii=False)}")
            
        else:
            return create_error_response(405, '지원하지 않는 메서드입니다.')
        
        if not response_data.get('success', True): # GET의 경우 success가 없음
            return create_error_response(400, response_data.get('error', '알 수 없는 오류'))

        return {
            'statusCode': status_code, 
            'headers': get_cors_headers(), 
            'body': json.dumps(response_data, ensure_ascii=False, cls=DecimalEncoder)
        }
            
    except Exception as e:
        logger.error(f"핸들러 오류: {str(e)}", exc_info=True)
        return create_error_response(500, f'서버 오류: {str(e)}')

def get_cors_headers():
    return {
        'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps(
            {'error': message, 'timestamp': datetime.utcnow().isoformat()},
            ensure_ascii=False,
            cls=DecimalEncoder
        )
    }