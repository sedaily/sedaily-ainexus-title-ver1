import json
import boto3
import os
import logging
from typing import Dict, Any, List

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3')

# 환경 변수
PROMPT_META_TABLE = os.environ['PROMPT_META_TABLE']
OPENSEARCH_ENDPOINT = os.environ['OPENSEARCH_ENDPOINT']
REGION = os.environ['REGION']

# 카테고리별 프롬프트 우선순위
PROMPT_CATEGORIES = [
    'title_type_guidelines',
    'stylebook_guidelines', 
    'workflow',
    'audience_optimization',
    'seo_optimization',
    'digital_elements_guidelines',
    'quality_assessment',
    'uncertainty_handling',
    'output_format',
    'description',
    'knowledge'
]

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions에서 호출되는 프롬프트 조회 핸들러
    """
    try:
        logger.info(f"프롬프트 조회 요청: {json.dumps(event, indent=2)}")
        
        project_id = event.get('projectId')
        if not project_id:
            raise ValueError("projectId가 필요합니다")
        
        # 프로젝트의 모든 프롬프트 조회
        prompts = get_project_prompts(project_id)
        
        if not prompts:
            raise ValueError(f"프로젝트 {project_id}에 프롬프트가 없습니다")
        
        logger.info(f"프롬프트 조회 완료: {len(prompts)}개")
        
        return {
            'statusCode': 200,
            'prompts': prompts,
            'projectId': project_id
        }
        
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        raise

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """
    프로젝트의 모든 프롬프트를 조회하고 S3에서 텍스트 로드
    """
    try:
        table = dynamodb.Table(PROMPT_META_TABLE)
        
        # 프로젝트의 모든 프롬프트 조회
        response = table.query(
            KeyConditionExpression='projectId = :projectId',
            ExpressionAttributeValues={':projectId': project_id}
        )
        
        if not response['Items']:
            logger.warning(f"프로젝트 {project_id}에 프롬프트가 없습니다")
            return []
        
        # 카테고리별로 정렬
        prompts_by_category = {}
        for item in response['Items']:
            category = item['category']
            prompts_by_category[category] = item
        
        # 우선순위 순서대로 프롬프트 조회 및 텍스트 로드
        prompts = []
        for category in PROMPT_CATEGORIES:
            if category in prompts_by_category:
                prompt_item = prompts_by_category[category]
                
                # S3에서 실제 프롬프트 텍스트 로드
                prompt_text = load_prompt_text_from_s3(prompt_item['fullPath'])
                
                if prompt_text:
                    prompts.append({
                        'category': category,
                        'fileName': prompt_item['fileName'],
                        'text': prompt_text,
                        'textLength': len(prompt_text)
                    })
        
        return prompts
        
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        raise

def load_prompt_text_from_s3(s3_path: str) -> str:
    """S3에서 프롬프트 텍스트 로드"""
    try:
        # S3 경로에서 버킷명과 키 분리
        session = boto3.Session()
        account_id = session.get_credentials().access_key
        bucket_name = f"bedrock-diy-prompts-{account_id}-{REGION}"
        
        response = s3_client.get_object(Bucket=bucket_name, Key=s3_path)
        return response['Body'].read().decode('utf-8')
        
    except Exception as e:
        logger.error(f"S3 프롬프트 로드 실패: {s3_path} - {str(e)}")
        return "" 