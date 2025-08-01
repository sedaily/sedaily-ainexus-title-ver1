"""
관리자 전용 프롬프트 카드 저장 및 평가 Lambda 함수
- 관리자만 프롬프트 카드 생성/수정 가능
- 단계별 평가 프로세스 지원
- 실시간 사고 과정 로깅
- 승인된 프롬프트는 GlobalPromptLibrary에 저장
"""

import json
import boto3
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb')

# 환경 변수에서 테이블 참조 (기존 CDK 테이블 사용)
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', 'title-generator-prompt-meta')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET', 'title-generator-prompts')
REGION = os.environ.get('REGION', 'us-east-1')

# DynamoDB 테이블 참조
prompt_meta_table = dynamodb.Table(PROMPT_META_TABLE)
s3_client = boto3.client('s3', region_name=REGION)

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON으로 변환하는 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

class PromptCardManager:
    """프롬프트 카드 관리 클래스 - 단계별 실행 지원"""
    
    def __init__(self):
        self.prompt_table = prompt_meta_table
        self.s3_client = s3_client
        self.bucket_name = PROMPT_BUCKET
    
    def create_prompt_card(self, admin_id: str, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """새로운 프롬프트 카드를 생성"""
        try:
            # 입력 검증
            title = card_data.get('title', '').strip()
            # prompt_text 또는 content 필드 모두 지원
            content = card_data.get('prompt_text', card_data.get('content', '')).strip()
            category = card_data.get('category', 'general')
            steps = card_data.get('steps', [])
            threshold = card_data.get('threshold', 0.7)  # 기본 임계값
            
            if not title:
                return {'success': False, 'error': '제목이 필요합니다.'}
            if not content:
                return {'success': False, 'error': '내용이 필요합니다.'}
            
            # 새 카드 생성
            card_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # DynamoDB에 모든 데이터 저장 (S3 사용하지 않음)
            card_item = {
                'promptId': card_id,
                'title': title,
                'content': content,  # 프롬프트 내용을 DynamoDB에 직접 저장
                'category': category,
                'isActive': True,
                'createdAt': timestamp,
                'updatedAt': timestamp,
                'adminId': admin_id,
                'threshold': Decimal(str(threshold)),
                'stepCount': len(steps),
                'hasSteps': len(steps) > 0,
                'tags': card_data.get('tags', []),
                'steps': steps if steps else []
            }
            
            self.prompt_table.put_item(Item=card_item)
            logger.info(f"프롬프트 카드 생성: {card_id} by admin {admin_id}")
            
            return {
                'success': True,
                'cardId': card_id,
                'message': '프롬프트 카드가 생성되었습니다.'
            }
            
        except Exception as e:
            logger.error(f"카드 생성 실패: {str(e)}")
            return {'success': False, 'error': str(e)}

    def start_evaluation_process(self, card_id: str, version: str, admin_id: str) -> str:
        """프롬프트 카드 평가 프로세스 시작"""
        session_id = str(uuid.uuid4())
        
        try:
            # 첫 번째 사고 로그
            self.log_agent_thought(
                session_id, 
                card_id, 
                0, 
                "planning", 
                f"프롬프트 카드 {card_id} 버전 {version}에 대한 평가를 시작합니다."
            )
            
            # 평가 Lambda 비동기 호출
            lambda_client = boto3.client('lambda')
            evaluation_payload = {
                "cardId": card_id,
                "version": version,
                "adminId": admin_id,
                "sessionId": session_id
            }
            
            # 비동기 호출 (Event 타입)
            lambda_client.invoke(
                FunctionName=os.environ.get('PROMPT_EVALUATION_FUNCTION', 'PromptEvaluationFunction'),
                InvocationType='Event',  # 비동기 호출
                Payload=json.dumps(evaluation_payload)
            )
            
            logger.info(f"평가 Lambda 호출됨: {session_id} for card {card_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"평가 프로세스 시작 실패: {str(e)}")
            # 실패해도 세션 ID는 반환 (로깅 목적)
            return session_id
    
    def log_agent_thought(self, session_id: str, card_id: str, step_number: int, 
                         thought_type: str, content: str) -> None:
        """에이전트 사고 과정을 로그에 기록"""
        timestamp = datetime.now(timezone.utc).isoformat()
        sequence = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        
        # TTL: 30일 후 자동 삭제
        ttl = int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 60 * 60)
        
        thought_item = {
            'PK': f'SESSION#{session_id}',
            'SK': f'THOUGHT#{timestamp}#{sequence}',
            'cardId': card_id,
            'stepNumber': step_number,
            'thoughtType': thought_type,
            'content': content,
            'timestamp': timestamp,
            'ttl': ttl
        }
        
        thoughts_table.put_item(Item=thought_item)
    
    def get_admin_cards(self, admin_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """관리자의 프롬프트 카드 목록 조회"""
        try:
            if status:
                # 특정 상태의 카드만 조회
                response = admin_cards_table.query(
                    IndexName='GSI1-CardStatus',
                    KeyConditionExpression='GSI1PK = :gsi1pk',
                    ExpressionAttributeValues={
                        ':gsi1pk': f'ADMIN#{admin_id}#STATUS#{status}'
                    }
                )
            else:
                # 모든 카드 조회
                response = admin_cards_table.query(
                    KeyConditionExpression='PK = :pk',
                    ExpressionAttributeValues={
                        ':pk': f'ADMIN#{admin_id}'
                    }
                )
            
            cards = []
            for item in response.get('Items', []):
                # Decimal 타입 변환
                clean_item = {k: (int(v) if isinstance(v, Decimal) else v) for k, v in item.items()}
                cards.append(clean_item)
            
            return cards
            
        except Exception as e:
            logger.error(f"관리자 카드 조회 실패: {str(e)}")
            return []

# PromptCardManager 인스턴스 생성
prompt_manager = PromptCardManager()

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    관리자 전용 프롬프트 카드 저장 및 관리 핸들러
    
    예상 요청:
    POST /save-prompt - 새 프롬프트 카드 생성
    GET /save-prompt - 관리자의 프롬프트 카드 목록 조회
    GET /prompts - 프롬프트 카드 목록 조회 (프론트엔드 호환)
    """
    logger.info(f"Handler started - Method: {event.get('httpMethod')}, Path: {event.get('path')}")
    
    try:
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        # CORS 처리
        if http_method == 'OPTIONS':
            return create_cors_response()
        
        # 요청 데이터 파싱
        body = json.loads(event.get('body', '{}')) if event.get('body') else {}
        query_params = event.get('queryStringParameters') or {}
        
        # /prompts 엔드포인트 처리 (프론트엔드 호환)
        if '/prompts' in path and http_method == 'GET':
            # projectId 없이 모든 활성화된 프롬프트 카드 조회
            include_content = query_params.get('includeContent', 'false').lower() == 'true'
            
            try:
                # prompt_meta_table에서 활성화된 프롬프트 카드 스캔
                response = prompt_meta_table.scan(
                    FilterExpression='isActive = :active',
                    ExpressionAttributeValues={
                        ':active': True
                    },
                    ProjectionExpression='promptId, title, tags, createdAt, updatedAt, threshold, content, isActive'
                )
                
                cards = []
                for item in response.get('Items', []):
                    card = {
                        'promptId': item.get('promptId'),
                        'prompt_id': item.get('promptId'),  # 프론트엔드 호환성
                        'title': item.get('title', ''),
                        'tags': item.get('tags', []),
                        'threshold': float(item.get('threshold', 0.7)),
                        'createdAt': item.get('createdAt', ''),
                        'updatedAt': item.get('updatedAt', ''),
                        'isActive': True,
                        'enabled': True  # 프론트엔드 호환성
                    }
                    
                    # includeContent가 true인 경우 DynamoDB에서 직접 content 포함
                    if include_content:
                        # content 필드를 prompt_text로 매핑 (프론트엔드 호환성)
                        card['prompt_text'] = item.get('content', '')
                        card['content'] = item.get('content', '')  # 프론트엔드 호환성
                    else:
                        # includeContent가 false여도 항상 prompt_text 포함
                        card['prompt_text'] = item.get('content', '')
                        card['content'] = item.get('content', '')
                    
                    cards.append(card)
                
                return create_success_response({
                    'success': True,
                    'promptCards': cards,
                    'cards': cards,  # 프론트엔드 호환성
                    'count': len(cards)
                })
                
            except Exception as e:
                logger.error(f"프롬프트 카드 조회 실패: {str(e)}")
                return create_error_response(500, f'프롬프트 카드 조회 실패: {str(e)}')
        
        # 관리자 ID 확인 (기존 /save-prompt 엔드포인트)
        admin_id = body.get('adminId') or query_params.get('adminId')
        if not admin_id:
            return create_error_response(400, 'adminId가 필요합니다.')
        
        # TODO: JWT 토큰 검증 및 관리자 권한 확인
        # if not is_admin(admin_id):
        #     return create_error_response(403, '관리자 권한이 필요합니다.')
        
        response_data = {}
        status_code = 200
        
        if http_method == 'POST' and '/prompts' in path:
            # 새 프롬프트 카드 생성 - /prompts 엔드포인트용
            logger.info("Creating new prompt card via /prompts endpoint")
            body['adminId'] = body.get('adminId', 'default')  # 기본 adminId 설정
            response_data = prompt_manager.create_prompt_card(body.get('adminId', 'default'), body)
            if response_data.get('success'):
                status_code = 201
                
        elif http_method == 'POST':
            # 새 프롬프트 카드 생성 - /save-prompt 엔드포인트용
            logger.info(f"Creating new prompt card for admin {admin_id}")
            response_data = prompt_manager.create_prompt_card(admin_id, body)
            if response_data.get('success'):
                status_code = 201
                
        elif http_method == 'GET':
            # 관리자의 프롬프트 카드 목록 조회
            status_filter = query_params.get('status')
            cards = prompt_manager.get_admin_cards(admin_id, status_filter)
            response_data = {
                'success': True,
                'cards': cards,
                'count': len(cards)
            }
            
        elif http_method == 'PUT':
            # 프롬프트 카드 업데이트
            path_params = event.get('pathParameters', {})
            prompt_id = path_params.get('promptId')
            
            if not prompt_id:
                return create_error_response(400, 'promptId가 필요합니다.')
            
            # 업데이트할 필드 준비
            update_data = {
                'title': body.get('title'),
                # prompt_text를 우선적으로 사용, 없으면 content 사용
                'content': body.get('prompt_text') or body.get('content', ''),
                'tags': body.get('tags', []),
                'isActive': body.get('isActive', True),
                'threshold': body.get('threshold', 0.7)
            }
            
            try:
                # DynamoDB 업데이트 (content 포함)
                prompt_meta_table.update_item(
                    Key={'promptId': prompt_id},
                    UpdateExpression='SET title = :title, content = :content, tags = :tags, isActive = :active, threshold = :threshold, updatedAt = :updated',
                    ExpressionAttributeValues={
                        ':title': update_data['title'],
                        ':content': update_data['content'],
                        ':tags': update_data['tags'],
                        ':active': update_data['isActive'],
                        ':threshold': Decimal(str(update_data['threshold'])),
                        ':updated': datetime.now(timezone.utc).isoformat()
                    }
                )
                
                response_data = {
                    'success': True,
                    'message': '프롬프트 카드가 업데이트되었습니다.',
                    'promptId': prompt_id
                }
                
            except Exception as e:
                logger.error(f"프롬프트 카드 업데이트 실패: {str(e)}")
                return create_error_response(500, f'업데이트 실패: {str(e)}')
            
        elif http_method == 'DELETE':
            # 프롬프트 카드 삭제 (논리적 삭제)
            path_params = event.get('pathParameters', {})
            prompt_id = path_params.get('promptId')
            
            if not prompt_id:
                return create_error_response(400, 'promptId가 필요합니다.')
            
            try:
                # DynamoDB에서 논리적 삭제 (isActive = false)
                prompt_meta_table.update_item(
                    Key={'promptId': prompt_id},
                    UpdateExpression='SET isActive = :active, updatedAt = :updated',
                    ExpressionAttributeValues={
                        ':active': False,
                        ':updated': datetime.now(timezone.utc).isoformat()
                    }
                )
                
                response_data = {
                    'success': True,
                    'message': '프롬프트 카드가 삭제되었습니다.',
                    'promptId': prompt_id
                }
                
            except Exception as e:
                logger.error(f"프롬프트 카드 삭제 실패: {str(e)}")
                return create_error_response(500, f'삭제 실패: {str(e)}')
            
        else:
            return create_error_response(405, '지원하지 않는 메서드입니다.')
        
        # 실패한 경우 에러 응답
        if not response_data.get('success', True):
            return create_error_response(400, response_data.get('error', '알 수 없는 오류'))
        
        return create_success_response(response_data, status_code)
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return create_error_response(500, f'서버 오류: {str(e)}')

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }

def create_cors_response() -> Dict[str, Any]:
    """CORS preflight 응답"""
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': ''
    }

def create_success_response(data: Dict[str, Any], status_code: int = 200) -> Dict[str, Any]:
    """성공 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps(data, ensure_ascii=False, cls=DecimalEncoder)
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': False
        }, ensure_ascii=False, cls=DecimalEncoder)
    }