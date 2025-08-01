"""
단계별 프롬프트 실행 엔진
- 각 단계별로 프롬프트를 실행하고 임계값을 평가
- 사고과정을 실시간으로 스트리밍
- LangGraph를 사용한 워크플로우 관리
"""

import json
import boto3
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

logger = logging.getLogger(__name__)

class StepStatus(Enum):
    """단계 실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StepResult:
    """단계 실행 결과"""
    step_id: str
    status: StepStatus
    response: str
    confidence: float
    reasoning: str
    next_action: str
    metadata: Dict[str, Any]

@dataclass
class ThoughtProcess:
    """사고 과정"""
    timestamp: str
    step_name: str
    thought: str
    reasoning: str
    confidence: float
    decision: str

class StepwisePromptExecutor:
    """단계별 프롬프트 실행 엔진"""
    
    def __init__(self, bedrock_client, stream_callback: Optional[Callable] = None):
        self.bedrock_client = bedrock_client
        self.stream_callback = stream_callback
        self.thoughts = []
        
    def execute_prompt_chain(
        self, 
        prompt_cards: List[Dict[str, Any]], 
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """프롬프트 체인 실행"""
        
        if not prompt_cards:
            return {
                "success": False,
                "error": "프롬프트 카드가 없습니다."
            }
        
        # LangGraph 사용 가능한 경우
        if LANGGRAPH_AVAILABLE:
            return self._execute_with_langgraph(prompt_cards, user_input, context)
        else:
            return self._execute_sequential(prompt_cards, user_input, context)
    
    def _execute_sequential(
        self, 
        prompt_cards: List[Dict[str, Any]], 
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """순차적 실행 (LangGraph 없이)"""
        
        results = []
        current_context = context or {}
        current_context['user_input'] = user_input
        
        for idx, card in enumerate(prompt_cards):
            # 사고과정 스트리밍
            self._stream_thought(ThoughtProcess(
                timestamp=datetime.now(timezone.utc).isoformat(),
                step_name=card.get('title', f'Step {idx + 1}'),
                thought=f"단계 {idx + 1} 시작: {card.get('title', '')}",
                reasoning="다음 단계를 실행하기 위해 준비 중입니다.",
                confidence=1.0,
                decision="PROCEED"
            ))
            
            # 단계 실행
            step_result = self._execute_single_step(card, current_context)
            results.append(step_result)
            
            # 임계값 평가
            if step_result.confidence < card.get('threshold', 0.7):
                self._stream_thought(ThoughtProcess(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    step_name=card.get('title', f'Step {idx + 1}'),
                    thought=f"임계값 미달: {step_result.confidence:.2f} < {card.get('threshold', 0.7)}",
                    reasoning=step_result.reasoning,
                    confidence=step_result.confidence,
                    decision="STOP"
                ))
                break
            
            # 컨텍스트 업데이트
            current_context[f'step_{idx}_result'] = step_result.response
            
        return {
            "success": True,
            "results": results,
            "thoughts": self.thoughts,
            "final_response": results[-1].response if results else ""
        }
    
    def _execute_with_langgraph(
        self, 
        prompt_cards: List[Dict[str, Any]], 
        user_input: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """LangGraph를 사용한 실행"""
        
        # 상태 정의
        class PromptState(dict):
            """프롬프트 실행 상태"""
            pass
        
        # 워크플로우 생성
        workflow = StateGraph(PromptState)
        
        # 각 단계를 노드로 추가
        for idx, card in enumerate(prompt_cards):
            node_name = f"step_{idx}"
            
            def create_step_function(card_data, step_idx):
                def step_function(state):
                    # 현재 컨텍스트 구성
                    current_context = {
                        'user_input': state.get('user_input', user_input),
                        **state
                    }
                    
                    # 단계 실행
                    result = self._execute_single_step(card_data, current_context)
                    
                    # 상태 업데이트
                    state[f'step_{step_idx}_result'] = result
                    state['last_result'] = result
                    
                    return state
                
                return step_function
            
            workflow.add_node(node_name, create_step_function(card, idx))
        
        # 엣지 추가 (조건부 진행)
        for idx in range(len(prompt_cards) - 1):
            current_node = f"step_{idx}"
            next_node = f"step_{idx + 1}"
            
            def create_condition_function(card_data, next_node_name):
                def should_continue(state):
                    last_result = state.get('last_result')
                    if last_result and last_result.confidence >= card_data.get('threshold', 0.7):
                        return next_node_name
                    return END
                
                return should_continue
            
            workflow.add_conditional_edges(
                current_node,
                create_condition_function(prompt_cards[idx], next_node)
            )
        
        # 시작 노드 설정
        workflow.set_entry_point("step_0")
        
        # 컴파일 및 실행
        app = workflow.compile()
        initial_state = PromptState(user_input=user_input, **(context or {}))
        
        # 실행
        final_state = app.invoke(initial_state)
        
        # 결과 수집
        results = []
        for idx in range(len(prompt_cards)):
            if f'step_{idx}_result' in final_state:
                results.append(final_state[f'step_{idx}_result'])
        
        return {
            "success": True,
            "results": results,
            "thoughts": self.thoughts,
            "final_response": results[-1].response if results else "",
            "execution_method": "langgraph"
        }
    
    def _execute_single_step(
        self, 
        card: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> StepResult:
        """단일 단계 실행"""
        
        try:
            # 프롬프트 구성
            prompt = self._build_step_prompt(card, context)
            
            # Bedrock 호출
            response = self._call_bedrock(prompt, card.get('modelId'))
            
            # 응답 분석
            analysis = self._analyze_response(response, card)
            
            return StepResult(
                step_id=card.get('promptId', 'unknown'),
                status=StepStatus.COMPLETED,
                response=response,
                confidence=analysis['confidence'],
                reasoning=analysis['reasoning'],
                next_action=analysis['next_action'],
                metadata={
                    'model': card.get('modelId', 'default'),
                    'tokens': analysis.get('token_count', 0)
                }
            )
            
        except Exception as e:
            logger.error(f"단계 실행 오류: {str(e)}")
            return StepResult(
                step_id=card.get('promptId', 'unknown'),
                status=StepStatus.FAILED,
                response="",
                confidence=0.0,
                reasoning=str(e),
                next_action="STOP",
                metadata={}
            )
    
    def _build_step_prompt(self, card: Dict[str, Any], context: Dict[str, Any]) -> str:
        """단계별 프롬프트 구성"""
        
        base_prompt = card.get('content', '')
        
        # 컨텍스트 주입
        if context:
            context_str = "\n\n=== 이전 단계 결과 ===\n"
            for key, value in context.items():
                if key.startswith('step_') and key.endswith('_result'):
                    context_str += f"{key}: {value}\n"
            
            base_prompt = f"{base_prompt}\n{context_str}"
        
        # 사용자 입력 추가
        if 'user_input' in context:
            base_prompt += f"\n\n사용자 입력: {context['user_input']}"
        
        return base_prompt
    
    def _call_bedrock(self, prompt: str, model_id: str = None) -> str:
        """Bedrock API 호출"""
        
        model_id = model_id or "apac.anthropic.claude-sonnet-4-20250514-v1:0"
        
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 65536,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "top_p": 0.9,
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body.get('content', [{}])[0].get('text', '')
            
        except Exception as e:
            logger.error(f"Bedrock 호출 오류: {str(e)}")
            raise
    
    def _analyze_response(self, response: str, card: Dict[str, Any]) -> Dict[str, Any]:
        """응답 분석 및 신뢰도 계산"""
        
        # 간단한 신뢰도 계산 (실제로는 더 복잡한 로직 필요)
        confidence = 0.8  # 기본값
        
        # 응답 길이 기반 조정
        if len(response) < 50:
            confidence -= 0.2
        elif len(response) > 500:
            confidence += 0.1
        
        # 특정 키워드 포함 여부
        positive_keywords = card.get('positive_keywords', ['완료', '성공', '확인'])
        negative_keywords = card.get('negative_keywords', ['실패', '오류', '불가능'])
        
        for keyword in positive_keywords:
            if keyword in response:
                confidence += 0.05
        
        for keyword in negative_keywords:
            if keyword in response:
                confidence -= 0.1
        
        # 범위 제한
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'confidence': confidence,
            'reasoning': f"응답 길이: {len(response)}, 긍정 키워드 포함 여부 확인",
            'next_action': "CONTINUE" if confidence >= card.get('threshold', 0.7) else "STOP",
            'token_count': len(response.split())  # 대략적인 토큰 수
        }
    
    def _stream_thought(self, thought: ThoughtProcess):
        """사고과정 스트리밍"""
        
        self.thoughts.append(thought)
        
        if self.stream_callback:
            self.stream_callback({
                "type": "thought_process",
                "data": {
                    "timestamp": thought.timestamp,
                    "step": thought.step_name,
                    "thought": thought.thought,
                    "reasoning": thought.reasoning,
                    "confidence": thought.confidence,
                    "decision": thought.decision
                }
            })