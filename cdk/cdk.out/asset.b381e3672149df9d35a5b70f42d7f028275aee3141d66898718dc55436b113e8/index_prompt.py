import json
import boto3
import os
import sys
import logging
from urllib.parse import unquote_plus
from typing import Dict, Any, List
from datetime import datetime

# Lambda Layer에서 FAISS 가져오기
sys.path.append('/opt/python')

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])

# 환경 변수
FAISS_BUCKET = os.environ.get('FAISS_BUCKET', '')
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', '')
REGION = os.environ.get('REGION', 'us-east-1')

# FAISS 매니저 임포트
try:
    from faiss_utils import FAISSManager
except ImportError:
    # 로컬 개발용 폴백
    import sys
    sys.path.append('../utils')
    from faiss_utils import FAISSManager

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    S3 이벤트 트리거 시 실행되는 메인 핸들러
    
    S3 → Titan Embeddings → FAISS 인덱스 업데이트 → DynamoDB 메타 저장 파이프라인
    """
    try:
        logger.info(f"S3 이벤트 수신: {json.dumps(event, indent=2)}")
        
        # FAISS 매니저 초기화
        faiss_manager = FAISSManager(FAISS_BUCKET, REGION)
        
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
                process_prompt_indexing(faiss_manager, bucket_name, object_key, parsed_info)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': '프롬프트 색인 완료'})
        }
        
    except Exception as e:
        logger.error(f"프롬프트 색인 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def parse_s3_object_info(object_key: str) -> Dict[str, str]:
    """
    S3 객체 키에서 프로젝트 정보 파싱
    예: prompts/project123/prompt456/content.txt
    """
    try:
        parts = object_key.split('/')
        if len(parts) >= 4 and parts[0] == 'prompts':
            return {
                'project_id': parts[1],
                'prompt_id': parts[2],
                'file_name': parts[3]
            }
    except Exception as e:
        logger.error(f"S3 객체 키 파싱 오류: {str(e)}")
    
    return {}

def process_prompt_indexing(faiss_manager: FAISSManager, bucket_name: str, object_key: str, parsed_info: Dict[str, str]) -> None:
    """프롬프트 색인 처리 메인 로직"""
    try:
        project_id = parsed_info['project_id']
        prompt_id = parsed_info['prompt_id']
        
        # S3에서 프롬프트 텍스트 로드
        prompt_text = load_prompt_from_s3(bucket_name, object_key)
        if not prompt_text:
            logger.warning(f"프롬프트 텍스트가 비어있습니다: {object_key}")
            return
        
        # DynamoDB에서 프롬프트 메타데이터 조회
        prompt_metadata = get_prompt_metadata(project_id, prompt_id)
        if not prompt_metadata:
            logger.warning(f"프롬프트 메타데이터를 찾을 수 없습니다: {project_id}/{prompt_id}")
            return
        
        # 검색용 텍스트 구성 (카테고리 + 제목 + 내용)
        search_text = build_search_text(prompt_metadata, prompt_text)
        
        # FAISS 인덱스 메타데이터 구성
        faiss_metadata = {
            'project_id': project_id,
            'prompt_id': prompt_id,
            'category': prompt_metadata.get('category', ''),
            'title': prompt_metadata.get('title', ''),
            'step_order': prompt_metadata.get('stepOrder', 0),
            'updated_at': datetime.utcnow().isoformat(),
            'text': prompt_text[:500],  # 검색 결과 표시용 텍스트 일부
            's3_key': object_key
        }
        
        # FAISS 인덱스 업데이트
        success = faiss_manager.update_index(
            project_id=project_id,
            new_texts=[search_text],
            new_metadata=[faiss_metadata]
        )
        
        if success:
            logger.info(f"FAISS 인덱스 업데이트 완료: {project_id}/{prompt_id}")
        else:
            logger.error(f"FAISS 인덱스 업데이트 실패: {project_id}/{prompt_id}")
            
    except Exception as e:
        logger.error(f"프롬프트 색인 처리 오류: {str(e)}")

def load_prompt_from_s3(bucket_name: str, object_key: str) -> str:
    """S3에서 프롬프트 텍스트 로드"""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"S3 텍스트 로드 오류: {str(e)}")
        return ""

def get_prompt_metadata(project_id: str, prompt_id: str) -> Dict[str, Any]:
    """DynamoDB에서 프롬프트 메타데이터 조회"""
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        response = table.get_item(
            Key={
                'projectId': project_id,
                'promptId': prompt_id
            }
        )
        return response.get('Item', {})
    except Exception as e:
        logger.error(f"DynamoDB 메타데이터 조회 오류: {str(e)}")
        return {}

def build_search_text(metadata: Dict[str, Any], content: str) -> str:
    """검색용 텍스트 구성"""
    parts = []
    
    # 카테고리
    if metadata.get('category'):
        parts.append(f"카테고리: {metadata['category']}")
    
    # 제목
    if metadata.get('title'):
        parts.append(f"제목: {metadata['title']}")
    
    # 내용
    if content:
        parts.append(f"내용: {content}")
    
    return "\n".join(parts)

def rebuild_project_index(project_id: str) -> bool:
    """프로젝트의 전체 FAISS 인덱스 재구축"""
    try:
        faiss_manager = FAISSManager(FAISS_BUCKET, REGION)
        
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
            prompt_text = load_prompt_from_s3(os.environ.get('PROMPT_BUCKET', ''), s3_key)
            
            if prompt_text:
                # 검색용 텍스트 구성
                search_text = build_search_text(item, prompt_text)
                
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
        
        # 인덱스 재구축
        if all_texts:
            return faiss_manager.rebuild_index(project_id, all_texts, all_metadata)
        else:
            logger.warning(f"프로젝트 {project_id}에 프롬프트가 없습니다.")
            return True
            
    except Exception as e:
        logger.error(f"인덱스 재구축 오류: {str(e)}")
        return False 