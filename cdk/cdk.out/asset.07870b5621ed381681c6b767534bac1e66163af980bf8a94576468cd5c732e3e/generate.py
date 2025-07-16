"""
AI 대화 생성 Lambda 함수 (LangChain 적용 버전)
- Runnable과 Memory를 사용하여 대화 기억 기능 구현
- 확장성과 유지보수성이 높은 구조
"""
import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

import boto3

# --- 기본 설정 ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ['REGION']
DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# --- Bedrock 클라이언트 초기화 ---
bedrock_client = boto3.client("bedrock-runtime", region_name=REGION)

ANTHROPIC_VERSION = "bedrock-2023-05-31"

# --- 유틸리티 함수 ---
def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

# --- 메인 핸들러 ---
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': get_cors_headers(), 'body': ''}

    try:
        body = json.loads(event.get('body', '{}'))
        path_params = event.get('pathParameters', {}) or {}
        
        project_id = path_params.get('projectId')
        user_input = body.get('userInput', '').strip()
        chat_history = body.get('chat_history', []) # 프론트에서 이전 대화 기록을 받아옴

        if not project_id or not user_input:
            return {'statusCode': 400, 'headers': get_cors_headers(), 'body': json.dumps({'message': '프로젝트 ID와 사용자 입력은 필수입니다.'})}

        # --- 동적 시스템 프롬프트 로드 ---
        # 이 부분은 변경되지 않습니다.
        from prompt_manager import SimplePromptManager
        prompt_manager = SimplePromptManager(
            prompt_bucket=os.environ.get('PROMPT_BUCKET', ''),
            prompt_meta_table=os.environ.get('PROMPT_META_TABLE', ''),
            region=REGION
        )
        prompts = prompt_manager.load_project_prompts(project_id)
        system_prompt = prompt_manager.combine_prompts(prompts, mode="system")

        # --- Bedrock 메시지 포맷 구성 (InvokeModel API 공식 사양 준수) ---
        
        # 1. 모든 메시지를 하나로 합치고, 역할이 같은 연속 메시지를 병합합니다.
        all_inputs = chat_history + [{"role": "user", "content": user_input}]
        
        merged_messages = []
        for msg in all_inputs:
            role = msg.get("role")
            content = msg.get("content", "").strip()

            if not content or role not in ["user", "assistant"]:
                continue

            if merged_messages and merged_messages[-1]["role"] == role:
                merged_messages[-1]["content"] += "\\n\\n" + content
            else:
                merged_messages.append({"role": role, "content": content})

        # 2. 대화가 assistant로 시작하는 경우를 방지합니다.
        if merged_messages and merged_messages[0]["role"] == "assistant":
            merged_messages.pop(0)

        # 3. 최종적으로 API 형식에 맞게 content를 객체 배열로 변환합니다.
        final_api_messages = []
        for msg in merged_messages:
            final_api_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            })
        
        messages = final_api_messages

        # --- Bedrock 호출 ---
        logger.info(f"Bedrock invoke 시작 (Project: {project_id})")
        
        body = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": 4096,  # 응답 길이를 넉넉하게 설정
            "temperature": 0.7,
            "messages": messages,
        }
        if system_prompt:
            body["system"] = system_prompt
        
        # --- 진단용 로그: Bedrock에 전달할 최종 body를 출력합니다 ---
        logger.info(f"Body to Bedrock: {json.dumps(body, ensure_ascii=False)}")

        response = bedrock_client.invoke_model(
            modelId=DEFAULT_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body).encode("utf-8"),
        )

        response_json = json.loads(response["body"].read())
        response_content = response_json["content"][0]["text"]
        logger.info("Bedrock invoke 완료")

        # 성공 응답 반환
        response_body = {
            'message': '응답이 생성되었습니다.',
            'result': response_content,
            'projectId': project_id,
            'mode': 'prompt_based' if prompts else 'direct_conversation',
            'model_info': {'model_used': DEFAULT_MODEL_ID},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response_body, ensure_ascii=False)
        }

    except Exception as e:
        logger.error(f"핸들러 오류: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': f'서버 오류: {str(e)}'}, ensure_ascii=False)
        } 