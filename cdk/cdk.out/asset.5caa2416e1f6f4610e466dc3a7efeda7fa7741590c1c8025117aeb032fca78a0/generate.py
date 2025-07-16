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
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

# --- 기본 설정 ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ['REGION']
DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# --- LangChain 모델 및 체인 초기화 ---
# 1. Bedrock LLM 초기화
model = ChatBedrock(
    model_id=DEFAULT_MODEL_ID,
    region_name=REGION,
    model_kwargs={"temperature": 0.7}
)

# 2. 대화 프롬프트 템플릿 설정
# - system: AI의 역할과 지시사항 (프롬프트 카드에서 동적으로 주입)
# - history: 대화 기록이 들어갈 자리 (메모리)
# - input: 현재 사용자의 질문이 들어갈 자리
prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

# 3. Runnable Chain (Memory 제거 버전)
chain = prompt_template | model | StrOutputParser()

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

        # --- 이전 대화 기록을 LangChain 메시지 객체로 변환 ---
        history_msgs = []
        for message in chat_history:
            if message.get('role') == 'user':
                history_msgs.append(HumanMessage(content=message.get('content', '')))
            elif message.get('role') == 'assistant':
                history_msgs.append(AIMessage(content=message.get('content', '')))
        
        # --- 체인 실행 ---
        logger.info(f"LangChain 체인 실행 시작 (Project: {project_id})")
        response_content = chain.invoke({
            "system_prompt": system_prompt,
            "input": user_input,
            "history": history_msgs
        })
        logger.info("LangChain 체인 실행 완료")

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