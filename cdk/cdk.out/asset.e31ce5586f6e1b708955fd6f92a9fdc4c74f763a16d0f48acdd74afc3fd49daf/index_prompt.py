import json
import boto3
import os
import hashlib
import logging
from urllib.parse import unquote_plus
from typing import Dict, Any, List
from datetime import datetime

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime', region_name=os.environ['REGION'])
opensearch_client = boto3.client('opensearchserverless', region_name=os.environ['REGION'])
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])

# 환경 변수
OPENSEARCH_ENDPOINT = os.environ.get('OPENSEARCH_ENDPOINT', '')
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', '')
INDEX_NAME = 'prompt-vectors'  # 일관된 인덱스 이름 사용

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    S3 이벤트 트리거 시 실행되는 메인 핸들러
    
    S3 → Titan Embeddings → OpenSearch → DynamoDB 메타 저장 파이프라인
    """
    try:
        logger.info(f"S3 이벤트 수신: {json.dumps(event, indent=2)}")
        
        # S3 이벤트 파싱
        for record in event['Records']:
            if record['eventName'].startswith('ObjectCreated'):
                bucket_name = record['s3']['bucket']['name']
                object_key = unquote_plus(record['s3']['object']['key'])
                
                logger.info(f"프롬프트 색인 시작: {bucket_name}/{object_key}")
                
                # S3 객체 정보 파싱
                parsed_info = parse_s3_object_info(object_key)
                if not parsed_info:
                    logger.warning(f"S3 객체 경로 파싱 실패: {object_key}")
                    continue
                
                # 프롬프트 색인 처리
                process_prompt_indexing(bucket_name, object_key, parsed_info)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': '프롬프트 색인 완료'})
        }
    
    except Exception as e:
        logger.error(f"프롬프트 색인 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def parse_s3_object_info(object_key: str) -> Dict[str, str]:
    """
    S3 객체 키에서 프로젝트 ID, 카테고리, 파일명 파싱
    
    형식: {projectId}/{category}/{fileName}
    예: abc-123/audience/audience_optimization.txt
    """
    parts = object_key.split('/')
    if len(parts) < 3:
        return None
    
    return {
        'projectId': parts[0],
        'category': parts[1],
        'fileName': parts[2],
        'fullPath': object_key
    }

def process_prompt_indexing(bucket_name: str, object_key: str, parsed_info: Dict[str, str]) -> None:
    """
    프롬프트 색인 처리 메인 로직
    """
    try:
        # 1. S3에서 프롬프트 텍스트 로드
        prompt_text = load_prompt_from_s3(bucket_name, object_key)
        
        # 2. 기존 임베딩 체크 (ETag 기반 중복 방지)
        s3_etag = get_s3_etag(bucket_name, object_key)
        if should_skip_indexing(parsed_info, s3_etag):
            logger.info(f"임베딩 이미 존재, 스킵: {object_key}")
            return
        
        # 3. Titan Embeddings 생성
        embedding_vector = create_embedding(prompt_text)
        
        # 4. OpenSearch에 저장
        save_to_opensearch(parsed_info, prompt_text, embedding_vector)
        
        # 5. DynamoDB 메타데이터 저장
        save_metadata_to_dynamodb(parsed_info, s3_etag, prompt_text)
        
        logger.info(f"프롬프트 색인 완료: {object_key}")
        
    except Exception as e:
        logger.error(f"프롬프트 색인 처리 중 오류: {str(e)}")
        raise

def load_prompt_from_s3(bucket_name: str, object_key: str) -> str:
    """S3에서 프롬프트 텍스트 로드"""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"S3 객체 로드 실패: {bucket_name}/{object_key} - {str(e)}")
        raise

def get_s3_etag(bucket_name: str, object_key: str) -> str:
    """S3 객체의 ETag 가져오기"""
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return response['ETag'].strip('"')
    except Exception as e:
        logger.error(f"S3 ETag 가져오기 실패: {bucket_name}/{object_key} - {str(e)}")
        raise

def should_skip_indexing(parsed_info: Dict[str, str], current_etag: str) -> bool:
    """
    DynamoDB에서 기존 ETag 확인하여 색인 스킵 여부 판단
    """
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        prompt_key = f"{parsed_info['category']}#{parsed_info['fileName']}"
        
        response = table.get_item(
            Key={
                'projectId': parsed_info['projectId'],
                'promptKey': prompt_key
            }
        )
        
        if 'Item' in response:
            stored_etag = response['Item'].get('etag', '')
            return stored_etag == current_etag
        
        return False
        
    except Exception as e:
        logger.warning(f"ETag 확인 중 오류, 색인 진행: {str(e)}")
        return False

def create_embedding(text: str) -> List[float]:
    """
    Amazon Titan Embeddings 모델을 사용하여 텍스트 임베딩 생성
    """
    try:
        # 텍스트가 너무 길면 트러케이션 (Titan 제한: 8192 토큰)
        if len(text) > 30000:  # 대략적인 문자 수 제한
            text = text[:30000] + "..."
        
        request_body = {
            "inputText": text,
            "dimensions": 1536,  # Titan Embeddings v1 기본 차원
            "normalize": True
        }
        
        response = bedrock_client.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            body=json.dumps(request_body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
        
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {str(e)}")
        raise

def save_to_opensearch(parsed_info: Dict[str, str], text: str, embedding: List[float]) -> None:
    """
    개선된 OpenSearch 문서 저장
    """
    try:
        # OpenSearch Python 클라이언트 사용
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        
        # AWS 인증 설정
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            os.environ['REGION'], 'es',
            session_token=credentials.token
        )
        
        # OpenSearch 클라이언트 생성
        client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        # 개선된 문서 구조
        doc = {
            "promptId": f"{parsed_info['projectId']}-{parsed_info['category']}-{parsed_info['fileName']}",
            "projectId": parsed_info['projectId'],
            "category": parsed_info['category'],
            "fileName": parsed_info['fileName'],
            "fullPath": parsed_info['fullPath'],
            "stepOrder": get_step_order_from_category(parsed_info['category']),
            "text_preview": text[:500],  # 전체 텍스트 대신 미리보기만
            "embedding": embedding,
            "keywords": extract_keywords_simple(text),
            "timestamp": datetime.utcnow().isoformat(),
            "textLength": len(text),
            "enabled": True
        }
        
        # 인덱스가 없으면 생성
        if not client.indices.exists(INDEX_NAME):
            create_opensearch_index(client)
        
        # 문서 저장
        response = client.index(
            index=INDEX_NAME,
            id=doc['promptId'],
            body=doc
        )
        
        logger.info(f"OpenSearch 저장 성공: {doc['promptId']} (result: {response['result']})")
        
    except ImportError:
        logger.warning("OpenSearch 라이브러리 없음 - 벡터 검색 비활성화")
    except Exception as e:
        logger.error(f"OpenSearch 저장 실패: {str(e)}")
        # OpenSearch 실패해도 전체 프로세스는 계속 진행

def create_opensearch_index(client):
    """OpenSearch 인덱스 생성"""
    index_body = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "promptId": {"type": "keyword"},
                "projectId": {"type": "keyword"},
                "category": {"type": "keyword"},
                "stepOrder": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib"
                    }
                },
                "text_preview": {"type": "text"},
                "keywords": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "enabled": {"type": "boolean"}
            }
        }
    }
    
    client.indices.create(INDEX_NAME, body=index_body)
    logger.info(f"OpenSearch 인덱스 생성 완료: {INDEX_NAME}")

def get_step_order_from_category(category: str) -> int:
    """카테고리에서 단계 순서 추출"""
    category_to_step = {
        'instruction': 1,
        'knowledge': 2,
        'secondary': 3,
        'style_guide': 4,
        'validation': 5,
        'enhancement': 6
    }
    return category_to_step.get(category, 1)

def extract_keywords_simple(text: str) -> List[str]:
    """간단한 키워드 추출"""
    words = text.lower().split()
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', '을', '를', '이', '가', '은', '는', '에', '의'}
    keywords = [w for w in words if len(w) > 2 and w not in common_words]
    return list(set(keywords))[:15]  # 상위 15개

def save_metadata_to_dynamodb(parsed_info: Dict[str, str], etag: str, text: str) -> None:
    """
    DynamoDB에 프롬프트 메타데이터 저장
    """
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        prompt_key = f"{parsed_info['category']}#{parsed_info['fileName']}"
        
        table.put_item(
            Item={
                'projectId': parsed_info['projectId'],
                'promptKey': prompt_key,
                'category': parsed_info['category'],
                'fileName': parsed_info['fileName'],
                'fullPath': parsed_info['fullPath'],
                'etag': etag,
                'textLength': len(text),
                'status': 'indexed',
                'indexedAt': datetime.utcnow().isoformat(),
                'title': extract_title_from_text(text)
            }
        )
        
        logger.info(f"DynamoDB 메타데이터 저장 성공: {prompt_key}")
        
    except Exception as e:
        logger.error(f"DynamoDB 메타데이터 저장 실패: {str(e)}")
        raise

def extract_title_from_text(text: str) -> str:
    """
    프롬프트 텍스트에서 제목 추출 (첫 번째 줄 또는 파일명 기반)
    """
    lines = text.strip().split('\n')
    if lines:
        title = lines[0].strip()
        if title and len(title) < 100:
            return title
    
    return "프롬프트" 