import json
import boto3
import os
import sys
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal
import hashlib

# Lambda Layer에서 FAISS 가져오기
sys.path.append('/opt/python')

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])

# 환경 변수
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
PROMPT_BUCKET = os.environ['PROMPT_BUCKET']
FAISS_BUCKET = os.environ.get('FAISS_BUCKET', '')
BEDROCK_EMBED_MODEL_ID = os.environ.get('BEDROCK_EMBED_MODEL_ID', 'amazon.titan-embed-text-v1')
REGION = os.environ['REGION']

# FAISS 유틸리티 임포트
try:
    from faiss_utils import FAISSManager
except ImportError:
    # 로컬 개발용 폴백
    import sys
    sys.path.append('../utils')
    from faiss_utils import FAISSManager

# 사용 가능한 모델 목록
AVAILABLE_MODELS = [
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-sonnet-20240229-v1:0",
    "us.anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-instant-v1",
    "amazon.titan-text-lite-v1",
    "amazon.titan-text-express-v1"
]

# 사용 가능한 카테고리 (6개 고정 카테고리) - 프론트엔드와 일치
AVAILABLE_CATEGORIES = [
    "instruction",    # 1단계: 역할 및 목표
    "knowledge",      # 2단계: 지식 베이스  
    "secondary",      # 3단계: CoT (사고 과정)
    "style_guide",    # 4단계: 스타일 가이드
    "validation",     # 5단계: ReAct (추론+행동)
    "enhancement"     # 6단계: 품질 검증
]

# 카테고리별 step_order 매핑
CATEGORY_STEP_ORDER = {
    "instruction": 1,   # 역할 및 목표
    "knowledge": 2,     # 지식 베이스
    "secondary": 3,     # CoT (사고 과정)
    "style_guide": 4,   # 스타일 가이드
    "validation": 5,    # ReAct (추론+행동)
    "enhancement": 6    # 품질 검증
}

# 카테고리 한글 이름 매핑
CATEGORY_NAMES = {
    "instruction": "역할 및 목표",
    "knowledge": "지식 베이스",
    "secondary": "CoT (사고 과정)",
    "style_guide": "스타일 가이드",
    "validation": "ReAct (추론+행동)",
    "enhancement": "품질 검증"
}

# OpenSearch 클라이언트 초기화
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth
    OPENSEARCH_AVAILABLE = True
except ImportError:
    logger.warning("OpenSearch 라이브러리 없음 - 벡터 검색 비활성화")
    OPENSEARCH_AVAILABLE = False

# FAISS 매니저 초기화
faiss_manager = None
if FAISS_BUCKET:
    try:
        faiss_manager = FAISSManager(FAISS_BUCKET, REGION)
        logger.info("FAISS 매니저 초기화 완료")
    except Exception as e:
        logger.error(f"FAISS 매니저 초기화 실패: {str(e)}")
        faiss_manager = None

class FAISSEmbeddingProcessor:
    """FAISS 기반 임베딩 처리 클래스"""
    
    def __init__(self):
        self.faiss_manager = faiss_manager
        
    def process_prompt_embedding(self, prompt_card: Dict[str, Any], prompt_text: str) -> bool:
        """프롬프트 임베딩 처리 및 FAISS 인덱스 업데이트"""
        try:
            if not self.faiss_manager:
                logger.warning("FAISS 매니저가 초기화되지 않음")
                return False
            
            project_id = prompt_card['projectId']
            prompt_id = prompt_card['promptId']
            
            # 검색용 텍스트 구성
            search_text = self._build_search_text(prompt_card, prompt_text)
            
            # FAISS 메타데이터 구성
            faiss_metadata = {
                'project_id': project_id,
                'prompt_id': prompt_id,
                'category': prompt_card.get('category', ''),
                'title': prompt_card.get('title', ''),
                'step_order': prompt_card.get('stepOrder', 0),
                'updated_at': datetime.utcnow().isoformat(),
                'text': prompt_text[:500],  # 검색 결과 표시용
                's3_key': f"prompts/{project_id}/{prompt_id}/content.txt"
            }
            
            # FAISS 인덱스 업데이트
            success = self.faiss_manager.update_index(
                project_id=project_id,
                new_texts=[search_text],
                new_metadata=[faiss_metadata]
            )
            
            if success:
                logger.info(f"FAISS 인덱스 업데이트 완료: {project_id}/{prompt_id}")
            else:
                logger.error(f"FAISS 인덱스 업데이트 실패: {project_id}/{prompt_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"FAISS 임베딩 처리 오류: {str(e)}")
            return False
    
    def _build_search_text(self, prompt_card: Dict[str, Any], content: str) -> str:
        """검색용 텍스트 구성"""
        parts = []
        
        # 카테고리
        if prompt_card.get('category'):
            parts.append(f"카테고리: {prompt_card['category']}")
        
        # 제목
        if prompt_card.get('title'):
            parts.append(f"제목: {prompt_card['title']}")
        
        # 내용
        if content:
            parts.append(f"내용: {content}")
        
        return "\n".join(parts)
    
    def remove_from_index(self, project_id: str, prompt_id: str) -> bool:
        """FAISS 인덱스에서 프롬프트 제거 (인덱스 재구축)"""
        try:
            if not self.faiss_manager:
                return False
            
            # 프로젝트의 모든 프롬프트를 다시 로드하여 인덱스 재구축
            # (FAISS는 개별 삭제가 어려우므로 재구축 방식 사용)
            return self._rebuild_project_index(project_id)
            
        except Exception as e:
            logger.error(f"FAISS 인덱스 제거 오류: {str(e)}")
            return False
    
    def _rebuild_project_index(self, project_id: str) -> bool:
        """프로젝트 전체 인덱스 재구축"""
        try:
            # DynamoDB에서 프로젝트의 모든 프롬프트 조회
            table = dynamodb.Table(PROMPT_META_TABLE)
            response = table.query(
                KeyConditionExpression='projectId = :pid',
                ExpressionAttributeValues={':pid': project_id}
            )
            
            all_texts = []
            all_metadata = []
            
            for item in response['Items']:
                prompt_id = item['promptId']
                
                # S3에서 프롬프트 내용 로드
                s3_key = f"prompts/{project_id}/{prompt_id}/content.txt"
                try:
                    response = s3_client.get_object(Bucket=PROMPT_BUCKET, Key=s3_key)
                    prompt_text = response['Body'].read().decode('utf-8')
                    
                    if prompt_text:
                        # 검색용 텍스트 구성
                        search_text = self._build_search_text(item, prompt_text)
                        
                        # 메타데이터 구성
                        metadata = {
                            'project_id': project_id,
                            'prompt_id': prompt_id,
                            'category': item.get('category', ''),
                            'title': item.get('title', ''),
                            'step_order': item.get('stepOrder', 0),
                            'updated_at': datetime.utcnow().isoformat(),
                            'text': prompt_text[:500],
                            's3_key': s3_key
                        }
                        
                        all_texts.append(search_text)
                        all_metadata.append(metadata)
                        
                except Exception as e:
                    logger.warning(f"프롬프트 로드 실패: {s3_key} - {str(e)}")
                    continue
            
            # 인덱스 재구축
            if all_texts:
                return self.faiss_manager.rebuild_index(project_id, all_texts, all_metadata)
            else:
                # 프롬프트가 없으면 인덱스 삭제
                return self.faiss_manager.delete_index(project_id)
                
        except Exception as e:
            logger.error(f"프로젝트 인덱스 재구축 오류: {str(e)}")
            return False

# 전역 임베딩 프로세서 인스턴스
embedding_processor = FAISSEmbeddingProcessor()

class PromptIndexer:
    """프롬프트 인덱싱 클래스"""
    
    def __init__(self):
        self.embedding_processor = embedding_processor
    
    def index_prompt(self, prompt_card: Dict[str, Any], prompt_text: str) -> bool:
        """프롬프트를 S3, DynamoDB, OpenSearch에 통합 인덱싱"""
        try:
            # 1. 임베딩 생성
            embedding = self.embedding_processor.process_prompt_embedding(prompt_card, prompt_text)
            if not embedding:
                logger.warning(f"임베딩 생성 실패: {prompt_card['promptId']}")
                return False
            
            # 2. OpenSearch에 벡터 저장
            if self.embedding_processor.faiss_manager: # FAISS 매니저가 있는 경우에만 OpenSearch 인덱싱
                opensearch_doc = {
                    'promptId': prompt_card['promptId'],
                    'projectId': prompt_card['projectId'],
                    'stepOrder': prompt_card.get('stepOrder', 1),
                    'category': prompt_card.get('category', 'instruction'),
                    'embedding': embedding,
                    'text_preview': prompt_text[:300],
                    'keywords': self._extract_keywords(prompt_text),
                    'created_at': datetime.utcnow().isoformat(),
                    's3Key': prompt_card.get('s3Key', '')
                }
                
                try:
                    self.embedding_processor.faiss_manager.update_index( # FAISS 매니저 사용
                        project_id=prompt_card['projectId'],
                        new_texts=[opensearch_doc['text_preview']],
                        new_metadata=[opensearch_doc]
                    )
                    logger.info(f"OpenSearch 인덱싱 성공: {prompt_card['promptId']}")
                except Exception as e:
                    logger.error(f"OpenSearch 인덱싱 실패: {str(e)}")
            
            # 3. S3에 임베딩 메타데이터 저장
            embedding_metadata = self.embedding_processor.faiss_manager.get_metadata( # FAISS 매니저 사용
                prompt_card['projectId'], prompt_card['promptId']
            )
            
            embedding_key = f"embeddings/{prompt_card['projectId']}/{prompt_card['promptId']}.json"
            s3_client.put_object(
                Bucket=PROMPT_BUCKET,
                Key=embedding_key,
                Body=json.dumps(embedding_metadata, ensure_ascii=False),
                ContentType='application/json'
            )
            
            # 4. DynamoDB 업데이트
            self._update_prompt_with_embedding_info(prompt_card, embedding_key, embedding_metadata)
            
            logger.info(f"프롬프트 통합 인덱싱 완료: {prompt_card['promptId']}")
            return True
            
        except Exception as e:
            logger.error(f"프롬프트 인덱싱 실패: {str(e)}")
            return False
    
    def _extract_keywords(self, text: str) -> List[str]:
        """간단한 키워드 추출"""
        words = text.lower().split()
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', '을', '를', '이', '가', '은', '는'}
        keywords = [w for w in words if len(w) > 2 and w not in common_words]
        return list(set(keywords))[:10]
    
    def _update_prompt_with_embedding_info(self, prompt_card: Dict[str, Any], embedding_key: str, embedding_metadata: Dict[str, Any]):
        """프롬프트 메타데이터에 임베딩 정보 추가"""
        try:
            table = dynamodb.Table(PROMPT_META_TABLE)
            table.update_item(
                Key={
                    'projectId': prompt_card['projectId'],
                    'promptId': prompt_card['promptId']
                },
                UpdateExpression='SET embeddingKey = :embeddingKey, embeddingId = :embeddingId, embeddingModel = :embeddingModel, indexedAt = :indexedAt',
                ExpressionAttributeValues={
                    ':embeddingKey': embedding_key,
                    ':embeddingId': embedding_metadata['prompt_id'], # FAISS 매니저에서 사용하는 prompt_id
                    ':embeddingModel': embedding_metadata['project_id'], # FAISS 매니저에서 사용하는 project_id
                    ':indexedAt': datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"임베딩 정보 업데이트 실패: {str(e)}")

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal 타입을 JSON 직렬화 가능한 타입으로 변환하는 커스텀 인코더"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    프롬프트 카드 저장/수정 메인 핸들러
    
    Routes:
    - PUT /prompts/{projectId}/{promptId}: 프롬프트 카드 저장/수정
    - POST /prompts/{projectId}: 새 프롬프트 카드 생성
    - GET /prompts/{projectId}: 프로젝트의 모든 프롬프트 카드 조회 (정렬)
    - DELETE /prompts/{projectId}/{promptId}: 프롬프트 카드 삭제
    """
    try:
        logger.info(f"프롬프트 카드 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'GET')
        path_parameters = event.get('pathParameters', {})
        project_id = path_parameters.get('projectId')
        prompt_id = path_parameters.get('promptId')
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        if not project_id:
            return create_error_response(400, "projectId가 필요합니다")
        
        if http_method == 'POST' and not prompt_id:
            return create_prompt_card(event)
        elif http_method == 'PUT' and prompt_id:
            return update_prompt_card(event)
        elif http_method == 'GET' and not prompt_id:
            return get_prompt_cards(event)
        elif http_method == 'DELETE' and prompt_id:
            return delete_prompt_card(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"프롬프트 카드 처리 중 오류 발생: {str(e)}")
        # 예외 발생 시에도 CORS 헤더 포함
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': f"내부 서버 오류: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }

def create_prompt_card(event: Dict[str, Any]) -> Dict[str, Any]:
    """새 프롬프트 카드 생성 (임베딩 포함)"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # 필수 필드 검증
        prompt_text = body.get('prompt_text', '').strip()
        category = body.get('category', '').strip()
        
        if not prompt_text:
            return create_error_response(400, "prompt_text가 필요합니다")
        
        if not category or category not in AVAILABLE_CATEGORIES:
            return create_error_response(400, f"유효한 category가 필요합니다: {AVAILABLE_CATEGORIES}")
        
        # 새 프롬프트 ID 생성
        prompt_id = str(uuid.uuid4())
        
        # 카테고리에 따른 step_order 자동 설정
        step_order = CATEGORY_STEP_ORDER.get(category, 1)
        
        # 프롬프트 카드 데이터 구성
        prompt_card = {
            'projectId': project_id,
            'promptId': prompt_id,
            'category': category,
            'stepOrder': step_order,  # 카테고리 기반 자동 설정
            'model': body.get('model', AVAILABLE_MODELS[0]),
            'temperature': Decimal(str(body.get('temperature', 0.7))),
            'enabled': body.get('enabled', True),
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'title': body.get('title', f"{CATEGORY_NAMES.get(category, category)} 프롬프트"),
            'description': body.get('description', ''),
            's3Key': f"prompts/{project_id}/{prompt_id}/content.txt"  # FAISS와 일치하는 경로 구조
        }
        
        # 모델 유효성 검증
        if prompt_card['model'] not in AVAILABLE_MODELS:
            return create_error_response(400, f"유효한 model이 필요합니다: {AVAILABLE_MODELS}")
        
        # S3에 프롬프트 텍스트 저장
        s3_key = prompt_card['s3Key']
        s3_client.put_object(
            Bucket=PROMPT_BUCKET,
            Key=s3_key,
            Body=prompt_text.encode('utf-8'),
            ContentType='text/plain',
            Metadata={
                'projectId': project_id,
                'promptId': prompt_id,
                'category': category,
                'stepOrder': str(step_order)
            }
        )
        
        # DynamoDB에 메타데이터 저장
        table = dynamodb.Table(PROMPT_META_TABLE)
        logger.info(f"DynamoDB에 프롬프트 카드 저장: {prompt_card}")
        table.put_item(Item=prompt_card)
        logger.info(f"DynamoDB 저장 완료: 프로젝트 {project_id}, 프롬프트 {prompt_id}, stepOrder {step_order}")
        
        # FAISS 인덱싱 (임베딩 생성 및 저장)
        indexing_success = embedding_processor.process_prompt_embedding(prompt_card, prompt_text)
        
        if not indexing_success:
            logger.warning(f"FAISS 인덱싱 실패했지만 카드 생성은 완료: {prompt_id}")
        
        logger.info(f"새 프롬프트 카드 생성 완료: {project_id}/{prompt_id}")
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps({
                **prompt_card,
                'indexed': indexing_success
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프롬프트 카드 생성 실패: {str(e)}")
        return create_error_response(500, f"프롬프트 카드 생성 실패: {str(e)}")

def update_prompt_card(event: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 카드 수정 (순서 변경 포함, 임베딩 재생성)"""
    try:
        project_id = event['pathParameters']['projectId']
        prompt_id = event['pathParameters']['promptId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # 기존 프롬프트 카드 조회
        table = dynamodb.Table(PROMPT_META_TABLE)
        response = table.get_item(
            Key={'projectId': project_id, 'promptId': prompt_id}
        )
        
        if 'Item' not in response:
            return create_error_response(404, "프롬프트 카드를 찾을 수 없습니다")
        
        existing_card = response['Item']
        
        # 업데이트할 필드들
        update_expression_parts = ["updatedAt = :updatedAt"]
        expression_values = {':updatedAt': datetime.utcnow().isoformat()}
        
        # 프롬프트 텍스트 업데이트 및 재인덱싱
        prompt_text_updated = False
        new_prompt_text = ""
        
        if 'prompt_text' in body:
            new_prompt_text = body['prompt_text'].strip()
            if new_prompt_text:
                # S3 업데이트
                s3_key = existing_card['s3Key']
                s3_client.put_object(
                    Bucket=PROMPT_BUCKET,
                    Key=s3_key,
                    Body=new_prompt_text.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'projectId': project_id,
                        'promptId': prompt_id,
                        'category': existing_card['category'],
                        'stepOrder': str(existing_card['stepOrder'])
                    }
                )
                prompt_text_updated = True
        
        # 다른 필드들 업데이트
        updatable_fields = ['category', 'model', 'temperature', 'enabled', 'title', 'description']
        for field in updatable_fields:
            if field in body:
                value = body[field]
                
                # 유효성 검증
                if field == 'category' and value not in AVAILABLE_CATEGORIES:
                    return create_error_response(400, f"유효한 category가 필요합니다: {AVAILABLE_CATEGORIES}")
                
                if field == 'model' and value not in AVAILABLE_MODELS:
                    return create_error_response(400, f"유효한 model이 필요합니다: {AVAILABLE_MODELS}")
                
                if field == 'temperature':
                    value = Decimal(str(value))
                
                update_expression_parts.append(f"{field} = :{field}")
                expression_values[f":{field}"] = value
        
        # step_order 변경 처리 (특별 로직)
        if 'step_order' in body:
            new_step_order = int(body['step_order'])
            handle_step_order_change(project_id, prompt_id, existing_card['stepOrder'], new_step_order)
            update_expression_parts.append("stepOrder = :stepOrder")
            expression_values[':stepOrder'] = new_step_order
        
        # DynamoDB 업데이트
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        response = table.update_item(
            Key={'projectId': project_id, 'promptId': prompt_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        updated_card = response['Attributes']
        
        # 프롬프트 텍스트가 변경된 경우 재인덱싱
        indexing_success = True
        if prompt_text_updated:
            indexing_success = embedding_processor.process_prompt_embedding(updated_card, new_prompt_text)
            
            if not indexing_success:
                logger.warning(f"FAISS 재인덱싱 실패: {prompt_id}")
        
        logger.info(f"프롬프트 카드 업데이트 완료: {project_id}/{prompt_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                **updated_card,
                'reindexed': indexing_success if prompt_text_updated else False
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프롬프트 카드 업데이트 실패: {str(e)}")
        return create_error_response(500, f"프롬프트 카드 업데이트 실패: {str(e)}")

def get_prompt_cards(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트의 모든 프롬프트 카드 조회 (step_order 순으로 정렬)"""
    try:
        project_id = event['pathParameters']['projectId']
        query_params = event.get('queryStringParameters') or {}
        
        # enabled 필터링 옵션
        include_disabled = query_params.get('include_disabled', 'false').lower() == 'true'
        
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # GSI를 사용하여 stepOrder 순으로 조회
        response = table.query(
            IndexName='projectId-stepOrder-index',
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id},
            ScanIndexForward=True  # stepOrder 오름차순 정렬
        )
        
        prompt_cards = response.get('Items', [])
        
        # enabled 필터링
        if not include_disabled:
            prompt_cards = [card for card in prompt_cards if card.get('enabled', True)]
        
        # S3에서 프롬프트 텍스트 로드 (옵션)
        if query_params.get('include_content', 'false').lower() == 'true':
            for card in prompt_cards:
                try:
                    s3_response = s3_client.get_object(
                        Bucket=PROMPT_BUCKET,
                        Key=card['s3Key']
                    )
                    card['prompt_text'] = s3_response['Body'].read().decode('utf-8')
                except Exception as e:
                    logger.warning(f"S3에서 프롬프트 텍스트 로드 실패: {card['s3Key']}, {str(e)}")
                    card['prompt_text'] = ""
        
        logger.info(f"프롬프트 카드 목록 조회: {project_id}, {len(prompt_cards)}개")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'projectId': project_id,
                'promptCards': prompt_cards,
                'count': len(prompt_cards)
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프롬프트 카드 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"프롬프트 카드 목록 조회 실패: {str(e)}")

def delete_prompt_card(event: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 카드 삭제"""
    try:
        project_id = event['pathParameters']['projectId']
        prompt_id = event['pathParameters']['promptId']
        
        # 기존 카드 조회
        table = dynamodb.Table(PROMPT_META_TABLE)
        response = table.get_item(
            Key={'projectId': project_id, 'promptId': prompt_id}
        )
        
        if 'Item' not in response:
            return create_error_response(404, "프롬프트 카드를 찾을 수 없습니다")
        
        existing_card = response['Item']
        
        # S3에서 파일 삭제
        try:
            s3_client.delete_object(
                Bucket=PROMPT_BUCKET,
                Key=existing_card['s3Key']
            )
        except Exception as e:
            logger.warning(f"S3 파일 삭제 실패: {existing_card['s3Key']}, {str(e)}")
        
        # DynamoDB에서 메타데이터 삭제
        table.delete_item(
            Key={'projectId': project_id, 'promptId': prompt_id}
        )
        
        # 다른 카드들의 step_order 재정렬
        reorder_remaining_cards(project_id, existing_card['stepOrder'])
        
        # FAISS 인덱스에서 프롬프트 제거
        if embedding_processor.faiss_manager:
            embedding_processor.remove_from_index(project_id, prompt_id)
        
        logger.info(f"프롬프트 카드 삭제: {project_id}/{prompt_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '프롬프트 카드가 삭제되었습니다',
                'projectId': project_id,
                'promptId': prompt_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"프롬프트 카드 삭제 실패: {str(e)}")
        return create_error_response(500, f"프롬프트 카드 삭제 실패: {str(e)}")

def get_next_step_order(project_id: str) -> int:
    """프로젝트의 다음 step_order 값 계산"""
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        response = table.query(
            IndexName='projectId-stepOrder-index',
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id},
            ScanIndexForward=False,  # 내림차순으로 정렬하여 최대값 조회
            Limit=1
        )
        
        items = response.get('Items', [])
        if items:
            return int(items[0]['stepOrder']) + 1
        else:
            return 1
            
    except Exception as e:
        logger.error(f"다음 step_order 계산 실패: {str(e)}")
        return 1

def handle_step_order_change(project_id: str, prompt_id: str, old_order: int, new_order: int):
    """step_order 변경 시 다른 카드들의 순서 조정"""
    if old_order == new_order:
        return
    
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # 프로젝트의 모든 카드 조회
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id}
        )
        
        all_cards = response.get('Items', [])
        
        # 현재 카드 제외
        other_cards = [card for card in all_cards if card['promptId'] != prompt_id]
        
        # 순서 재정렬 로직
        if old_order < new_order:
            # 뒤로 이동: old_order < stepOrder <= new_order인 카드들을 앞으로 한 칸씩
            for card in other_cards:
                step_order = int(card['stepOrder'])
                if old_order < step_order <= new_order:
                    table.update_item(
                        Key={'projectId': project_id, 'promptId': card['promptId']},
                        UpdateExpression='SET stepOrder = stepOrder - :one',
                        ExpressionAttributeValues={':one': 1}
                    )
        else:
            # 앞으로 이동: new_order <= stepOrder < old_order인 카드들을 뒤로 한 칸씩
            for card in other_cards:
                step_order = int(card['stepOrder'])
                if new_order <= step_order < old_order:
                    table.update_item(
                        Key={'projectId': project_id, 'promptId': card['promptId']},
                        UpdateExpression='SET stepOrder = stepOrder + :one',
                        ExpressionAttributeValues={':one': 1}
                    )
        
        logger.info(f"step_order 변경 처리 완료: {project_id}, {old_order} -> {new_order}")
        
    except Exception as e:
        logger.error(f"step_order 변경 처리 실패: {str(e)}")
        raise

def reorder_remaining_cards(project_id: str, deleted_order: int):
    """삭제된 카드 이후의 카드들 순서 재정렬"""
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # 삭제된 순서보다 큰 카드들 조회
        response = table.query(
            IndexName='projectId-stepOrder-index',
            KeyConditionExpression='projectId = :projectId AND stepOrder > :deletedOrder',
            ExpressionAttributeValues={
                ':projectId': project_id,
                ':deletedOrder': deleted_order
            }
        )
        
        cards_to_update = response.get('Items', [])
        
        # 각 카드의 stepOrder를 1씩 감소
        for card in cards_to_update:
            table.update_item(
                Key={'projectId': project_id, 'promptId': card['promptId']},
                UpdateExpression='SET stepOrder = stepOrder - :one',
                ExpressionAttributeValues={':one': 1}
            )
        
        logger.info(f"삭제 후 순서 재정렬 완료: {project_id}, {len(cards_to_update)}개 카드")
        
    except Exception as e:
        logger.error(f"삭제 후 순서 재정렬 실패: {str(e)}")

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
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