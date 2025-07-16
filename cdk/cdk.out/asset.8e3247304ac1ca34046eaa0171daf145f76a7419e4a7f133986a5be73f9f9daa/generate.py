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

        # --- Bedrock 메시지 포맷 구성 (안정성 강화 v2) ---
        # Bedrock Claude3는 매우 엄격한 메시지 규칙을 따릅니다.
        # 1. (선택) 시스템 프롬프트는 항상 첫 번째여야 함.
        # 2. 사용자(user)와 어시스턴트(assistant) 역할은 번갈아 나타나야 함.
        # 3. 대화는 항상 사용자(user) 역할로 시작해야 함 (시스템 프롬프트 제외).
        # 4. 같은 역할의 메시지가 연속될 수 없음.
        # 아래 로직은 어떤 history가 들어와도 이 규칙을 강제합니다.
        
        final_messages = []
        # 시스템 프롬프트는 메시지 배열에서 제외합니다.
        # if system_prompt:
        #     final_messages.append({"role": "system", "content": system_prompt})

        # chat_history와 현재 입력을 합쳐서 처리
        all_inputs = chat_history + [{"role": "user", "content": user_input}]

        last_role = None
        merged_content = ""

        # 연속된 역할을 하나로 합치고, 빈 메시지를 제거합니다.
        for message in all_inputs:
            role = message.get("role")
            content = message.get("content", "").strip()

            if not content or role not in ["user", "assistant"]:
                continue

            if role == last_role:
                merged_content += "\\n\\n" + content
            else:
                if last_role and merged_content:
                    final_messages.append({"role": last_role, "content": merged_content})
                last_role = role
                merged_content = content
        
        if last_role and merged_content:
            final_messages.append({"role": last_role, "content": merged_content})

        # 최종 유효성 검사: user-assistant 순서를 강제하고, assistant로 시작하는 것을 방지
        start_index = 1 if system_prompt else 0
        
        # 1. assistant로 시작하면 해당 메시지 제거
        if len(final_messages) > start_index and final_messages[start_index]["role"] == "assistant":
            del final_messages[start_index]

        # 2. 역할 순서가 깨진 곳(user-user 등)을 찾아 뒤쪽 메시지를 제거
        i = start_index
        while i < len(final_messages) - 1:
            if final_messages[i]["role"] == final_messages[i+1]["role"]:
                del final_messages[i+1]
            else:
                i += 1
        
        messages = final_messages

        # --- Bedrock 호출 ---
        logger.info(f"Bedrock invoke 시작 (Project: {project_id})")
        
        body = {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": 1024,
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