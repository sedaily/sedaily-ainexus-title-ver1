"""
AI 대화 생성 Lambda 함수 (단순화 버전)
- 프롬프트 카드 기반의 대화 생성에 집중
- 직접 Bedrock 모델을 호출하여 구조 단순화
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# prompt_manager는 계속 사용합니다.
from prompt_manager import SimplePromptManager

# --- AWS 클라이언트 및 환경 변수 ---
REGION = os.environ['REGION']
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', '')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET', '')
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']

bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# --- 기본 모델 설정 ---
DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
MODEL_CONFIG = {
    "max_tokens": 8192,
    "temperature": 0.7
}

def get_cors_headers():
    """CORS 프리플라이트 요청을 위한 헤더를 반환합니다."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

def _call_bedrock(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Bedrock의 Claude 3.5 Sonnet 모델을 직접 호출합니다."""
    try:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MODEL_CONFIG["max_tokens"],
            "temperature": MODEL_CONFIG["temperature"],
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}]
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=DEFAULT_MODEL_ID,
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        logger.info(f"모델 호출 성공: {DEFAULT_MODEL_ID}")
        return {"success": True, "content": content, "model_used": DEFAULT_MODEL_ID}
        
    except Exception as e:
        logger.error(f"모델({DEFAULT_MODEL_ID}) 호출 실패: {str(e)}")
        return {"success": False, "error": str(e), "model_attempted": DEFAULT_MODEL_ID}

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """메인 핸들러 - 프롬프트 카드 기반 대화 생성을 위한 단일 흐름"""
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': get_cors_headers(), 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
        
        # URL 경로에서 projectId를 가져오도록 수정
        path_params = event.get('pathParameters', {}) or {}
        project_id = path_params.get('projectId')
        
        user_input = body.get('userInput', '').strip()

        # 필수 파라미터 검증
        if not project_id or not user_input:
            error_msg = '프로젝트 ID와 사용자 입력은 필수입니다.'
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': error_msg}, ensure_ascii=False)
            }

        # 프롬프트 매니저 초기화 및 프롬프트 로드
        prompt_manager = SimplePromptManager(
            prompt_bucket=PROMPT_BUCKET,
            prompt_meta_table=PROMPT_META_TABLE,
            region=REGION
        )
        prompts = prompt_manager.load_project_prompts(project_id)
        system_prompt = prompt_manager.combine_prompts(prompts, mode="system")
        
        logger.info(f"프로젝트({project_id}) 대화 시작. 프롬프트 {len(prompts)}개, 시스템 프롬프트 {len(system_prompt)}자")

        # Bedrock 모델 호출
        result = _call_bedrock(system_prompt, user_input)

        if not result['success']:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'AI 응답 생성 중 오류가 발생했습니다.',
                    'error': result.get('error', 'Unknown error'),
                    'model_attempted': result.get('model_attempted')
                }, ensure_ascii=False)
            }

        # 성공 응답 반환
        response_body = {
            'message': '응답이 생성되었습니다.',
            'result': result['content'],
            'projectId': project_id,
            'mode': 'prompt_based' if prompts else 'direct_conversation',
            'model_info': {'model_used': result['model_used']},
            'prompt_info': {
                'prompt_count': len(prompts),
                'system_prompt_length': len(system_prompt)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        save_execution_record(project_id, user_input, result['content'], response_body['model_info'])

        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response_body, ensure_ascii=False)
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '잘못된 JSON 형식입니다.'}, ensure_ascii=False)
        }
    except Exception as e:
        logger.error(f"핸들러 오류: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': f'서버 오류: {str(e)}'}, ensure_ascii=False)
        }

def save_execution_record(project_id: str, user_input: str, result: str, model_info: Dict[str, Any]) -> None:
    """(선택적) 실행 기록을 DynamoDB에 저장합니다."""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        timestamp = datetime.utcnow()
        
        record = {
            'executionId': f"{project_id}_{int(timestamp.timestamp() * 1000)}",
            'projectId': project_id,
            'timestamp': timestamp.isoformat(),
            'inputLength': len(user_input),
            'outputLength': len(result),
            'modelInfo': model_info,
            'status': 'completed'
        }
        
        table.put_item(Item=record)
        
    except Exception as e:
        logger.warning(f"실행 기록 저장 실패: {str(e)}") 