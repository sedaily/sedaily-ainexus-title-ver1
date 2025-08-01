"""
사용자 정의 프롬프트 카드 기반 동적 LangGraph 워크플로우
"""
from typing import TypedDict, List, Dict, Any, Optional
import json
import os
import boto3

# LangGraph 의존성을 선택적으로 import
try:
    from langgraph.graph import StateGraph, END
    from langchain_aws import ChatBedrock
    LANGGRAPH_DEPS_AVAILABLE = True
except ImportError as e:
    print(f"LangGraph 의존성 없음: {e}")
    LANGGRAPH_DEPS_AVAILABLE = False
    
    # 더미 클래스들로 대체
    class StateGraph:
        def __init__(self, state_type): pass
        def add_node(self, name, func): pass
        def add_edge(self, from_node, to_node): pass
        def add_conditional_edges(self, node, condition, mapping): pass
        def set_entry_point(self, node): pass
        def compile(self): return self
        def invoke(self, state): return state
    
    END = "END"

class CustomWorkflowState(TypedDict):
    """사용자 맞춤 워크플로우 상태"""
    user_input: str
    user_prompt_cards: List[Dict[str, Any]]  # 사용자가 만든 프롬프트 카드들
    current_step: int
    step_results: List[Dict[str, Any]]
    accumulated_context: str
    final_answer: str
    websocket_connection: str

def create_dynamic_workflow_from_cards(prompt_cards: List[Dict[str, Any]]):
    """
    사용자의 프롬프트 카드를 기반으로 동적 워크플로우 생성
    
    Args:
        prompt_cards: [
            {
                "promptId": "card1",
                "title": "문제 분석",
                "prompt_text": "사용자의 질문을 분석하고 핵심 키워드를 추출하세요.",
                "stepOrder": 1
            },
            {
                "promptId": "card2", 
                "title": "솔루션 탐색",
                "prompt_text": "분석된 문제에 대한 3가지 해결 방안을 제시하세요.",
                "stepOrder": 2
            },
            ...
        ]
    """
    
    # 프롬프트 카드를 stepOrder로 정렬
    sorted_cards = sorted(prompt_cards, key=lambda x: x.get('stepOrder', 0))
    
    workflow = StateGraph(CustomWorkflowState)
    
    # 시작 노드
    workflow.add_node("initialize", initialize_workflow)
    
    # 각 프롬프트 카드를 개별 노드로 생성
    previous_node = "initialize"
    
    for i, card in enumerate(sorted_cards):
        node_name = f"step_{i+1}_{card['promptId']}"
        
        # 동적으로 실행 함수 생성
        def create_step_function(card_data):
            def execute_step(state: CustomWorkflowState) -> CustomWorkflowState:
                return execute_prompt_card_step(state, card_data)
            return execute_step
        
        # 노드 추가
        workflow.add_node(node_name, create_step_function(card))
        
        # 이전 노드와 연결
        workflow.add_edge(previous_node, node_name)
        previous_node = node_name
    
    # 최종 정리 노드
    workflow.add_node("finalize", finalize_custom_workflow)
    workflow.add_edge(previous_node, "finalize")
    workflow.add_edge("finalize", END)
    
    # 시작점 설정
    workflow.set_entry_point("initialize")
    
    return workflow.compile()

def initialize_workflow(state: CustomWorkflowState) -> CustomWorkflowState:
    """워크플로우 초기화"""
    connection_id = state["websocket_connection"]
    
    send_thinking_step(connection_id, {
        "type": "workflow_start",
        "title": "🚀 맞춤형 사고과정 시작",
        "message": f"{len(state['user_prompt_cards'])}단계의 사고과정을 시작합니다.",
        "total_steps": len(state["user_prompt_cards"])
    })
    
    state["current_step"] = 0
    state["step_results"] = []
    state["accumulated_context"] = ""
    
    return state

def execute_prompt_card_step(state: CustomWorkflowState, card: Dict[str, Any]) -> CustomWorkflowState:
    """개별 프롬프트 카드 실행"""
    connection_id = state["websocket_connection"]
    step_number = state["current_step"] + 1
    
    card_title = card.get("title", f"단계 {step_number}")
    card_prompt = card.get("prompt_text", "")
    
    # 사고과정 시작 알림
    send_thinking_step(connection_id, {
        "type": "step_start",
        "step_number": step_number,
        "title": f"🧠 {card_title}",
        "instruction": card_prompt,
        "status": "processing"
    })
    
    # 현재까지의 컨텍스트와 함께 프롬프트 구성
    full_prompt = build_contextual_prompt(
        user_input=state["user_input"],
        card_instruction=card_prompt,
        previous_context=state["accumulated_context"]
    )
    
    # Claude API 호출
    llm = ChatBedrock(
        model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        model_kwargs={"temperature": 0.3, "max_tokens": 65536}
    )
    
    try:
        response = llm.invoke([
            {"role": "user", "content": full_prompt}
        ])
        
        step_result = response.content
        
        # 결과 저장
        state["step_results"].append({
            "step": step_number,
            "card_id": card.get("promptId"),
            "title": card_title,
            "instruction": card_prompt,
            "result": step_result,
            "timestamp": "now"
        })
        
        # 누적 컨텍스트 업데이트
        state["accumulated_context"] += f"\n\n## {card_title}\n{step_result}"
        state["current_step"] = step_number
        
        # 단계 완료 알림
        send_thinking_step(connection_id, {
            "type": "step_complete",
            "step_number": step_number,
            "title": f"✅ {card_title} 완료",
            "result": step_result[:200] + "..." if len(step_result) > 200 else step_result,
            "full_result": step_result,
            "status": "completed"
        })
        
    except Exception as e:
        # 오류 처리
        error_msg = f"단계 {step_number} 실행 중 오류: {str(e)}"
        
        state["step_results"].append({
            "step": step_number,
            "card_id": card.get("promptId"),
            "title": card_title,
            "error": error_msg,
            "timestamp": "now"
        })
        
        send_thinking_step(connection_id, {
            "type": "step_error",
            "step_number": step_number,
            "title": f"❌ {card_title} 오류",
            "error": error_msg,
            "status": "error"
        })
    
    return state

def finalize_custom_workflow(state: CustomWorkflowState) -> CustomWorkflowState:
    """맞춤형 워크플로우 최종 정리"""
    connection_id = state["websocket_connection"]
    
    # 최종 답변 생성
    send_thinking_step(connection_id, {
        "type": "final_synthesis",
        "title": "🎯 최종 답변 생성",
        "message": "모든 단계의 결과를 종합하여 최종 답변을 생성합니다.",
        "status": "processing"
    })
    
    # 최종 답변 프롬프트
    synthesis_prompt = f"""
    다음은 사용자의 질문에 대해 단계별로 사고한 결과입니다:

    **원본 질문**: {state["user_input"]}

    **단계별 사고과정**:
    {state["accumulated_context"]}

    위의 모든 단계별 사고과정을 종합하여, 사용자의 질문에 대한 명확하고 완성도 높은 최종 답변을 작성해주세요.
    """
    
    llm = ChatBedrock(
        model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        model_kwargs={"temperature": 0.2, "max_tokens": 65536}
    )
    
    try:
        final_response = llm.invoke([
            {"role": "user", "content": synthesis_prompt}
        ])
        
        state["final_answer"] = final_response.content
        
        # 최종 답변 완료 알림
        send_thinking_step(connection_id, {
            "type": "workflow_complete",
            "title": "🎉 사고과정 완료",
            "message": "모든 단계의 사고과정을 거쳐 최종 답변이 완성되었습니다.",
            "summary": {
                "total_steps": len(state["step_results"]),
                "successful_steps": len([r for r in state["step_results"] if "error" not in r]),
                "final_answer": state["final_answer"]
            },
            "status": "completed"
        })
        
    except Exception as e:
        # 최종 단계 오류시 이전 결과들을 조합
        state["final_answer"] = state["accumulated_context"]
        
        send_thinking_step(connection_id, {
            "type": "workflow_error",
            "title": "⚠️ 최종 정리 중 오류",
            "message": "최종 정리 중 오류가 발생했지만, 단계별 결과를 제공합니다.",
            "error": str(e)
        })
    
    return state

def build_contextual_prompt(user_input: str, card_instruction: str, previous_context: str) -> str:
    """컨텍스트를 고려한 프롬프트 구성"""
    
    prompt_parts = []
    
    # 1. 사용자 원본 질문
    prompt_parts.append(f"**사용자 질문**: {user_input}")
    
    # 2. 이전 단계 결과 (있는 경우)
    if previous_context.strip():
        prompt_parts.append(f"**이전 단계 결과**:\n{previous_context}")
    
    # 3. 현재 단계 지시사항
    prompt_parts.append(f"**현재 단계 지시사항**:\n{card_instruction}")
    
    # 4. 실행 지침
    prompt_parts.append("""
**실행 지침**:
- 위의 지시사항을 정확히 따라 실행하세요
- 이전 단계 결과가 있다면 이를 참고하여 답변하세요
- 명확하고 구체적으로 답변해주세요
""")
    
    return "\n\n".join(prompt_parts)

def send_thinking_step(connection_id: str, step_data: Dict):
    """WebSocket으로 사고과정 전송"""
    # 실제 구현에서는 apigateway_client 사용
    print(f"WebSocket [{connection_id}]: {step_data}")
    
    # 실제 WebSocket 전송 로직
    try:
        import boto3
        apigateway_client = boto3.client('apigatewaymanagementapi', 
                                       endpoint_url=f"https://{os.environ.get('DOMAIN_NAME')}/{os.environ.get('STAGE')}")
        
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(step_data)
        )
    except Exception as e:
        print(f"WebSocket 전송 실패: {e}")

# 사용 예시
def create_user_workflow(user_prompt_cards: List[Dict[str, Any]]):
    """
    사용자가 만든 프롬프트 카드로 워크플로우 생성
    
    예시 사용:
    user_cards = [
        {
            "promptId": "analysis_card",
            "title": "문제 분석", 
            "prompt_text": "사용자의 질문을 분석하고 핵심 요소 3가지를 추출하세요.",
            "stepOrder": 1
        },
        {
            "promptId": "solution_card",
            "title": "해결방안 도출",
            "prompt_text": "분석된 문제에 대해 실용적인 해결방안을 제시하세요.",
            "stepOrder": 2
        },
        {
            "promptId": "validation_card", 
            "title": "답변 검증",
            "prompt_text": "제시된 해결방안의 장단점을 분석하고 개선점을 제안하세요.",
            "stepOrder": 3
        }
    ]
    
    workflow = create_user_workflow(user_cards)
    """
    return create_dynamic_workflow_from_cards(user_prompt_cards)