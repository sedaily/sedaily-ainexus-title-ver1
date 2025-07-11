import os
import json
import re
from pathlib import Path

import streamlit as st
import anthropic
from dotenv import load_dotenv

# 환경 변수(.env) 로드
auth_loaded = load_dotenv()

# Anthropic 클라이언트 초기화
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 프롬프트 파일 로드 (캐싱)
@st.cache_resource
def load_prompts():
    text_dir = Path(__file__).parent / "text"
    with open(text_dir / "instruction.txt", "r", encoding="utf-8") as f:
        instruction = f.read()
    with open(text_dir / "description.txt", "r", encoding="utf-8") as f:
        description = f.read()
    with open(text_dir / "knowledge.txt", "r", encoding="utf-8") as f:
        knowledge = f.read()
    return {
        "instruction": instruction,
        "description": description,
        "knowledge": knowledge,
    }

prompts = load_prompts()

# Streamlit UI -----------------------------
# (set_page_config already called at top)
# st.set_page_config(page_title="TITLE-NOMICS – AI 제목 생성기", layout="wide")
st.title("📰 TITLE-NOMICS AI 제목 생성기")

# API 키가 없으면 경고
if not os.getenv("ANTHROPIC_API_KEY") and not auth_loaded:
    st.warning("환경 변수 ANTHROPIC_API_KEY 가 설정되어 있지 않습니다. .env 파일이나 환경 변수로 설정해주세요.")

article_content = st.text_area(
    "기사 원문을 입력하세요 (최대 8,000자 권장)", height=300
)

col_generate, col_empty = st.columns([1, 4])
with col_generate:
    generate = st.button("제목 생성", type="primary")

if generate:
    if not article_content.strip():
        st.warning("기사 내용을 입력해주세요.")
        st.stop()

    with st.spinner("Claude가 제목을 생성 중입니다… 잠시만 기다려주세요."):
        system_prompt = (
            "당신은 서울경제신문의 TITLE-NOMICS AI 제목 생성 시스템입니다.\n\n"
            f"프로젝트 설명:\n{prompts['description']}\n\n"
            f"핵심 지식:\n{prompts['knowledge']}\n\n"
            f"상세 지침:\n{prompts['instruction']}\n\n"
            "위의 모든 지침을 철저히 따라서 제목을 생성해주세요."
        )

        user_prompt = (
            "다음 기사 원문에 대해 TITLE-NOMICS 시스템의 6단계 워크플로우를 따라 제목을 생성해주세요.\n\n"
            f"기사 원문:\n{article_content}\n\n"
            "출력 형식은 다음과 같이 JSON 형태로 해주세요:\n"  # 예시는 생략하고 모델에 맡김
        )

        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # 빠른 응답을 위해 Haiku 사용
                max_tokens=2048,
                temperature=0.5,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            response_text = response.content[0].text
            match = re.search(r"\{[\s\S]*\}", response_text)
            if match:
                result = json.loads(match.group())
            else:
                result = {"error": "JSON 파싱 실패", "raw": response_text}

        except Exception as e:
            st.error(f"제목 생성 중 오류가 발생했습니다: {e}")
            st.stop()

        # 결과 출력 ---------------------------------
        if "error" in result:
            st.error(result["error"])
            with st.expander("Claude 원본 응답 보기"):
                st.text(result.get("raw", ""))
            st.stop()

        # 분석 결과
        st.header("🔍 분석 결과")
        analysis = result.get("analysis", {})
        for key, value in analysis.items():
            st.markdown(f"**{key}**: {value}")

        # 카테고리별 제목
        st.header("📝 생성된 제목")
        titles = result.get("titles", {})
        for category, lst in titles.items():
            with st.expander(category.upper()):
                if not lst:
                    st.write("생성된 제목이 없습니다.")
                    continue
                for idx, item in enumerate(lst, 1):
                    st.markdown(f"**{idx}. {item.get('title', '')}**")
                    evaluation = item.get("evaluation", {})
                    if evaluation:
                        st.json(evaluation, expanded=False)

        # 최종 추천
        final_rec = result.get("final_recommendation", {})
        st.header("🏆 최종 추천 제목")
        st.subheader(final_rec.get("title", "(제목 없음)"))
        st.write(f"유형: {final_rec.get('type', '')}")
        st.caption(final_rec.get("reason", ""))

        st.success("제목 생성이 완료되었습니다!")