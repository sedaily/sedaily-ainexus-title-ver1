"""
LangGraph 기반 사고과정 추적 워크플로우
"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
import json

class ThinkingState(TypedDict):
    """사고과정 상태 관리"""
    user_input: str
    prompt_cards: List[Dict[str, Any]]
    current_context: Dict[str, Any]
    thinking_steps: List[Dict[str, Any]]
    final_answer: str
    confidence_score: float
    websocket_connection: str

def analyze_question(state: ThinkingState) -> ThinkingState:
    """1단계: 사용자 질문 분석"""
    user_input = state["user_input"]
    connection_id = state["websocket_connection"]
    
    # WebSocket으로 진행상황 전송
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "question_analysis",
        "title": "🔍 질문 분석 중...",
        "thought": f"사용자의 질문을 분석하고 있습니다: '{user_input[:50]}...'",
        "reasoning": "질문의 의도와 핵심 키워드를 파악하고 있습니다.",
        "status": "processing"
    })
    
    # 질문 분석 로직
    analysis = {
        "question_type": classify_question_type(user_input),
        "key_entities": extract_key_entities(user_input),
        "intent": analyze_user_intent(user_input),
        "complexity": assess_complexity(user_input)
    }
    
    state["thinking_steps"].append({
        "step": "question_analysis",
        "result": analysis,
        "confidence": 0.8
    })
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "question_analysis",
        "title": "✅ 질문 분석 완료",
        "thought": f"질문 유형: {analysis['question_type']}, 복잡도: {analysis['complexity']}",
        "reasoning": "질문의 구조와 요구사항을 파악했습니다.",
        "status": "completed"
    })
    
    return state

def select_relevant_prompts(state: ThinkingState) -> ThinkingState:
    """2단계: 관련 프롬프트 카드 선택"""
    connection_id = state["websocket_connection"]
    prompt_cards = state["prompt_cards"]
    question_analysis = state["thinking_steps"][-1]["result"]
    
    send_thinking_step(connection_id, {
        "type": "thinking_step", 
        "step": "prompt_selection",
        "title": "🎯 적절한 프롬프트 선택 중...",
        "thought": f"{len(prompt_cards)}개의 프롬프트 카드에서 최적의 조합을 찾고 있습니다.",
        "reasoning": "질문 유형에 맞는 프롬프트를 선별합니다.",
        "status": "processing"
    })
    
    # 프롬프트 선택 로직
    selected_prompts = []
    for card in prompt_cards:
        relevance_score = calculate_relevance(card, question_analysis)
        if relevance_score > 0.5:
            selected_prompts.append({
                "card": card,
                "relevance": relevance_score
            })
    
    # 관련도 순으로 정렬
    selected_prompts.sort(key=lambda x: x["relevance"], reverse=True)
    
    state["thinking_steps"].append({
        "step": "prompt_selection",
        "result": selected_prompts,
        "confidence": 0.9
    })
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "prompt_selection", 
        "title": "✅ 프롬프트 선택 완료",
        "thought": f"{len(selected_prompts)}개의 관련 프롬프트를 선택했습니다.",
        "reasoning": "가장 적합한 프롬프트 조합을 결정했습니다.",
        "status": "completed"
    })
    
    return state

def generate_initial_response(state: ThinkingState) -> ThinkingState:
    """3단계: 초기 답변 생성"""
    connection_id = state["websocket_connection"]
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "initial_generation", 
        "title": "💭 초기 답변 생성 중...",
        "thought": "선택된 프롬프트를 바탕으로 첫 번째 답변을 생성합니다.",
        "reasoning": "체계적인 사고 과정을 통해 답변을 구성합니다.",
        "status": "processing"
    })
    
    # Claude API 호출로 초기 답변 생성
    selected_prompts = state["thinking_steps"][-1]["result"]
    system_prompt = build_system_prompt(selected_prompts)
    
    llm = ChatBedrock(
        model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        model_kwargs={"temperature": 0.3, "max_tokens": 65536}
    )
    
    initial_response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_input"]}
    ])
    
    state["thinking_steps"].append({
        "step": "initial_generation",
        "result": initial_response.content,
        "confidence": 0.7
    })
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "initial_generation",
        "title": "✅ 초기 답변 생성 완료", 
        "thought": "첫 번째 답변이 생성되었습니다.",
        "reasoning": "이제 이 답변을 검토하고 개선할 차례입니다.",
        "status": "completed"
    })
    
    return state

def self_critique(state: ThinkingState) -> ThinkingState:
    """4단계: 자가 비판 및 검토"""
    connection_id = state["websocket_connection"]
    initial_response = state["thinking_steps"][-1]["result"]
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "self_critique",
        "title": "🤔 답변 자가 검토 중...", 
        "thought": "생성된 답변의 품질과 정확성을 검토합니다.",
        "reasoning": "더 나은 답변을 위해 비판적 사고를 적용합니다.",
        "status": "processing"
    })
    
    # 자가 비판 프롬프트
    critique_prompt = f"""
    다음 답변을 비판적으로 검토하세요:
    
    질문: {state["user_input"]}
    답변: {initial_response}
    
    검토 기준:
    1. 정확성: 사실적 오류가 있는가?
    2. 완성도: 질문에 충분히 답했는가?
    3. 명확성: 이해하기 쉬운가?
    4. 관련성: 질문과 관련이 있는가?
    
    개선점과 점수(1-10)를 제시하세요.
    """
    
    llm = ChatBedrock(
        model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        model_kwargs={"temperature": 0.1, "max_tokens": 65536}
    )
    
    critique_result = llm.invoke([
        {"role": "user", "content": critique_prompt}
    ])
    
    state["thinking_steps"].append({
        "step": "self_critique", 
        "result": critique_result.content,
        "confidence": 0.8
    })
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "self_critique",
        "title": "✅ 자가 검토 완료",
        "thought": "답변의 강점과 개선점을 파악했습니다.",
        "reasoning": "검토 결과를 바탕으로 답변 개선 여부를 결정합니다.",
        "status": "completed"
    })
    
    return state

def should_refine(state: ThinkingState) -> str:
    """개선 필요성 판단"""
    critique = state["thinking_steps"][-1]["result"]
    
    # 점수 추출 (간단한 휴리스틱)
    if "점수" in critique and any(str(i) in critique for i in range(1, 7)):
        return "refine"
    elif "우수" in critique or "완벽" in critique:
        return "finalize"
    else:
        return "refine"

def refine_answer(state: ThinkingState) -> ThinkingState:
    """5단계: 답변 개선"""
    connection_id = state["websocket_connection"]
    initial_response = state["thinking_steps"][2]["result"]
    critique = state["thinking_steps"][-1]["result"]
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "refinement",
        "title": "🔧 답변 개선 중...",
        "thought": "비판적 검토를 바탕으로 답변을 개선합니다.",
        "reasoning": "더 정확하고 완성도 높은 답변을 만들어갑니다.",
        "status": "processing"
    })
    
    refinement_prompt = f"""
    다음 답변을 개선하세요:
    
    원래 질문: {state["user_input"]}
    초기 답변: {initial_response}
    검토 의견: {critique}
    
    검토 의견을 반영하여 더 나은 답변을 작성하세요.
    """
    
    llm = ChatBedrock(
        model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0", 
        model_kwargs={"temperature": 0.2, "max_tokens": 65536}
    )
    
    refined_response = llm.invoke([
        {"role": "user", "content": refinement_prompt}
    ])
    
    state["final_answer"] = refined_response.content
    state["confidence_score"] = 0.9
    
    state["thinking_steps"].append({
        "step": "refinement",
        "result": refined_response.content,
        "confidence": 0.9
    })
    
    send_thinking_step(connection_id, {
        "type": "thinking_step",
        "step": "refinement", 
        "title": "✅ 답변 개선 완료",
        "thought": "최종 개선된 답변이 준비되었습니다.",
        "reasoning": "사고과정을 통해 고품질 답변을 완성했습니다.",
        "status": "completed"
    })
    
    return state

def finalize_answer(state: ThinkingState) -> ThinkingState:
    """최종답변 확정"""
    if not state.get("final_answer"):
        # 개선 단계를 거치지 않은 경우
        state["final_answer"] = state["thinking_steps"][2]["result"]
        state["confidence_score"] = 0.8
    
    return state

# 워크플로우 그래프 생성
def create_thinking_workflow():
    """사고과정 추적 워크플로우 생성"""
    
    workflow = StateGraph(ThinkingState)
    
    # 노드 추가
    workflow.add_node("analyze_question", analyze_question)
    workflow.add_node("select_prompts", select_relevant_prompts) 
    workflow.add_node("generate_initial", generate_initial_response)
    workflow.add_node("self_critique", self_critique)
    workflow.add_node("refine_answer", refine_answer)
    workflow.add_node("finalize", finalize_answer)
    
    # 엣지 연결
    workflow.set_entry_point("analyze_question")
    workflow.add_edge("analyze_question", "select_prompts")
    workflow.add_edge("select_prompts", "generate_initial") 
    workflow.add_edge("generate_initial", "self_critique")
    
    # 조건부 엣지
    workflow.add_conditional_edges(
        "self_critique",
        should_refine,
        {
            "refine": "refine_answer",
            "finalize": "finalize"
        }
    )
    
    workflow.add_edge("refine_answer", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

# 헬퍼 함수들
def classify_question_type(question: str) -> str:
    """질문 유형 분류"""
    if "?" in question:
        if any(word in question.lower() for word in ["what", "무엇", "뭐"]):
            return "정의/설명"
        elif any(word in question.lower() for word in ["how", "어떻게"]):
            return "방법/절차"
        elif any(word in question.lower() for word in ["why", "왜"]):
            return "이유/원인"
    return "일반"

def extract_key_entities(question: str) -> List[str]:
    """핵심 키워드 추출"""
    # 간단한 키워드 추출 (실제로는 더 정교한 NLP 사용)
    words = question.split()
    return [word for word in words if len(word) > 2]

def analyze_user_intent(question: str) -> str:
    """사용자 의도 분석"""
    if any(word in question.lower() for word in ["help", "도움", "도와"]):
        return "도움요청"
    elif any(word in question.lower() for word in ["explain", "설명"]):
        return "설명요청"
    return "정보요청"

def assess_complexity(question: str) -> str:
    """질문 복잡도 평가"""
    word_count = len(question.split())
    if word_count < 5:
        return "단순"
    elif word_count < 15:
        return "보통"
    else:
        return "복잡"

def calculate_relevance(card: Dict, analysis: Dict) -> float:
    """프롬프트 카드 관련도 계산"""
    # 간단한 키워드 매칭 기반 관련도 계산
    card_text = card.get("prompt_text", "").lower()
    question_entities = analysis.get("key_entities", [])
    
    matches = sum(1 for entity in question_entities if entity.lower() in card_text)
    return matches / max(len(question_entities), 1)

def build_system_prompt(selected_prompts: List[Dict]) -> str:
    """시스템 프롬프트 구성"""
    prompt_parts = []
    for prompt_info in selected_prompts:
        card = prompt_info["card"]
        prompt_parts.append(card.get("prompt_text", ""))
    
    return "\n\n".join(prompt_parts)

def send_thinking_step(connection_id: str, step_data: Dict):
    """WebSocket으로 사고과정 전송"""
    # 실제 구현에서는 apigateway_client 사용
    print(f"WebSocket [{connection_id}]: {step_data}")