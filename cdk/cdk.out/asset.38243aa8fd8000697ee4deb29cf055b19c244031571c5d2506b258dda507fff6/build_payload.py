import json
import boto3
import os
import logging
from typing import Dict, Any, List

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 환경 변수
REGION = os.environ['REGION']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions에서 호출되는 Bedrock 페이로드 준비 핸들러
    """
    try:
        logger.info(f"페이로드 준비 요청: {json.dumps(event, indent=2)}")
        
        prompts = event.get('prompts', [])
        article = event.get('article', '')
        project_id = event.get('projectId', '')
        
        if not prompts:
            raise ValueError("프롬프트가 필요합니다")
        
        if not article:
            raise ValueError("기사 내용이 필요합니다")
        
        # 프롬프트들을 결합
        combined_prompts = combine_prompts(prompts)
        
        # 시스템 프롬프트와 사용자 프롬프트 준비
        system_prompt, user_prompt = prepare_prompts(combined_prompts, article)
        
        # 토큰 길이 체크 및 조정
        system_prompt, user_prompt = adjust_prompt_length(system_prompt, user_prompt)
        
        # Bedrock 모델 호출을 위한 페이로드 생성
        payload = create_bedrock_payload(system_prompt, user_prompt)
        
        logger.info(f"페이로드 준비 완료: {len(system_prompt)}자 + {len(user_prompt)}자")
        
        return {
            'statusCode': 200,
            'body': payload,
            'systemPromptLength': len(system_prompt),
            'userPromptLength': len(user_prompt),
            'projectId': project_id
        }
        
    except Exception as e:
        logger.error(f"페이로드 준비 실패: {str(e)}")
        raise

def combine_prompts(prompts: List[Dict[str, Any]]) -> str:
    """
    프롬프트들을 결합하여 하나의 텍스트로 만듦
    """
    try:
        combined_text = ""
        for prompt in prompts:
            category = prompt.get('category', '')
            text = prompt.get('text', '')
            
            if text:
                combined_text += f"\n\n=== {category.upper()} ===\n{text}"
        
        return combined_text.strip()
        
    except Exception as e:
        logger.error(f"프롬프트 결합 실패: {str(e)}")
        raise

def prepare_prompts(combined_prompts: str, article_text: str) -> tuple:
    """시스템 프롬프트와 사용자 프롬프트 준비"""
    
    system_prompt = f"""당신은 서울경제신문의 TITLE-NOMICS AI 제목 생성 시스템입니다.

다음은 제목 생성을 위한 모든 가이드라인과 지침입니다:

{combined_prompts}

위의 모든 지침을 철저히 따라서 제목을 생성해주세요.
반드시 JSON 형식으로 응답하고, 다양한 카테고리의 제목을 제공하며, 최종 추천 제목을 선정해주세요."""

    user_prompt = f"""다음 기사 원문에 대해 TITLE-NOMICS 시스템의 6단계 워크플로우를 따라 제목을 생성해주세요.

기사 원문:
{article_text}

다음과 같은 JSON 형식으로 응답해주세요:
{{
  "analysis": {{
    "main_topic": "기사의 핵심 주제",
    "target_audience": "대상 독자층",
    "key_keywords": ["핵심", "키워드", "리스트"],
    "tone": "기사의 톤앤매너",
    "urgency": "긴급성/시급성 레벨"
  }},
  "titles": {{
    "straight": [
      {{"title": "직설적 제목", "evaluation": {{"clarity": 85, "impact": 70}}}},
      {{"title": "또 다른 직설적 제목", "evaluation": {{"clarity": 90, "impact": 75}}}}
    ],
    "question": [
      {{"title": "질문형 제목", "evaluation": {{"engagement": 80, "curiosity": 90}}}}
    ],
    "impact": [
      {{"title": "임팩트 제목", "evaluation": {{"shock": 95, "shareability": 85}}}}
    ]
  }},
  "final_recommendation": {{
    "title": "최종 추천 제목",
    "type": "제목 유형",
    "reason": "선정 이유 및 기대 효과"
  }}
}}"""

    return system_prompt, user_prompt

def adjust_prompt_length(system_prompt: str, user_prompt: str) -> tuple:
    """
    프롬프트 길이를 조정하여 토큰 제한 내에 맞춤
    """
    try:
        # 대략적인 토큰 계산 (1토큰 ≈ 4자)
        max_tokens = 180000  # Claude 3.5 Sonnet 200K 토큰 제한
        current_length = len(system_prompt) + len(user_prompt)
        
        if current_length > max_tokens:
            logger.warning(f"프롬프트가 너무 길어서 요약합니다: {current_length} -> {max_tokens}")
            
            # 시스템 프롬프트를 우선 보존하고 사용자 프롬프트를 줄임
            if len(system_prompt) > max_tokens * 0.7:
                system_prompt = system_prompt[:int(max_tokens * 0.7)]
                user_prompt = user_prompt[:int(max_tokens * 0.3)]
            else:
                remaining_tokens = max_tokens - len(system_prompt)
                user_prompt = user_prompt[:remaining_tokens]
        
        return system_prompt, user_prompt
        
    except Exception as e:
        logger.error(f"프롬프트 길이 조정 실패: {str(e)}")
        return system_prompt, user_prompt

def create_bedrock_payload(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Bedrock 모델 호출을 위한 페이로드 생성
    """
    try:
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.7,
            "top_p": 0.9,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        }
        
        return payload
        
    except Exception as e:
        logger.error(f"Bedrock 페이로드 생성 실패: {str(e)}")
        raise 