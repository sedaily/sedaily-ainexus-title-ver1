"""
LangGraph 기반 프롬프트 평가 워크플로우
- 단계별 평가 (품질, 명확성, 완성도 등)
- 실시간 사고 과정 로깅
- 임계값 기반 통과/실패 판정
- 재시도 로직 포함
"""

import json
import boto3
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict
from decimal import Decimal
import uuid

# LangGraph imports
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트
dynamodb = boto3.resource('dynamodb')

# 테이블 참조
admin_cards_table = dynamodb.Table(os.environ['ADMIN_PROMPT_CARDS_TABLE'])
global_library_table = dynamodb.Table(os.environ['GLOBAL_PROMPT_LIBRARY_TABLE'])
evaluations_table = dynamodb.Table(os.environ['PROMPT_EVALUATIONS_TABLE'])
thoughts_table = dynamodb.Table(os.environ['AGENT_THOUGHTS_TABLE'])
step_config_table = dynamodb.Table(os.environ['STEP_CONFIGURATIONS_TABLE'])

class EvaluationState(TypedDict):
    """평가 워크플로우 상태"""
    card_id: str
    version: str
    admin_id: str
    session_id: str
    current_step: int
    title: str
    content: str
    category: str
    scores: Dict[str, float]
    feedback: Dict[str, str]
    overall_passed: bool
    retry_count: int
    max_retries: int
    step_configs: List[Dict[str, Any]]

class PromptEvaluationWorkflow:
    """프롬프트 평가 워크플로우 관리 클래스"""
    
    def __init__(self):
        """Claude 3.5 Sonnet 모델 초기화"""
        self.llm = ChatBedrock(
            model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
            model_kwargs={
                "max_tokens": 65536,
                "temperature": 0.1,
                "top_p": 0.9
            }
        )
        
        # 기본 단계 설정
        self.default_steps = [
            {
                "stepNumber": 1,
                "stepName": "품질_평가",
                "threshold": 0.75,
                "evaluationPrompt": """
다음 프롬프트의 품질을 0-1 점수로 평가해주세요.

평가 기준:
1. 명확성: 지시사항이 명확하고 이해하기 쉬운가?
2. 구체성: 원하는 결과가 구체적으로 명시되어 있는가?
3. 완성도: 필요한 모든 정보가 포함되어 있는가?
4. 실행가능성: 실제로 실행 가능한 지시사항인가?

프롬프트:
{content}

응답 형식:
{{
  "score": 0.0-1.0,
  "feedback": "상세한 평가 의견"
}}
"""
            },
            {
                "stepNumber": 2,
                "stepName": "안전성_검토",
                "threshold": 0.8,
                "evaluationPrompt": """
다음 프롬프트의 안전성을 0-1 점수로 평가해주세요.

검토 기준:
1. 유해 콘텐츠: 폭력, 혐오, 불법적 내용이 없는가?
2. 개인정보: 개인정보 유출 위험이 없는가?  
3. 편향성: 특정 집단에 대한 편향이나 차별이 없는가?
4. 윤리성: 윤리적으로 적절한 내용인가?

프롬프트:
{content}

응답 형식:
{{
  "score": 0.0-1.0,
  "feedback": "안전성 검토 의견"
}}
"""
            },
            {
                "stepNumber": 3,
                "stepName": "효과성_평가",
                "threshold": 0.7,
                "evaluationPrompt": """
다음 프롬프트의 효과성을 0-1 점수로 평가해주세요.

평가 기준:
1. 목적 달성도: 의도한 목적을 달성할 수 있는가?
2. 결과 예측성: 일관된 결과를 생성할 수 있는가?
3. 사용성: 다양한 상황에서 활용 가능한가?
4. 창의성: 창의적이고 혁신적인 결과를 유도하는가?

프롬프트:
{content}

응답 형식:
{{
  "score": 0.0-1.0,
  "feedback": "효과성 평가 의견"
}}
"""
            }
        ]
    
    def create_workflow(self) -> StateGraph:
        """평가 워크플로우 그래프 생성"""
        workflow = StateGraph(EvaluationState)
        
        # 노드 추가
        workflow.add_node("load_prompt", self.load_prompt_data)
        workflow.add_node("load_config", self.load_step_configurations)
        workflow.add_node("evaluate_step", self.evaluate_current_step)
        workflow.add_node("check_result", self.check_step_result)
        workflow.add_node("next_step", self.move_to_next_step)
        workflow.add_node("retry_step", self.retry_current_step)
        workflow.add_node("finalize", self.finalize_evaluation)
        workflow.add_node("approve_prompt", self.approve_to_library)
        
        # 시작점 설정
        workflow.set_entry_point("load_prompt")
        
        # 엣지 연결
        workflow.add_edge("load_prompt", "load_config")
        workflow.add_edge("load_config", "evaluate_step")
        workflow.add_edge("evaluate_step", "check_result")
        
        # 조건부 라우팅
        workflow.add_conditional_edges(
            "check_result",
            self.should_continue,
            {
                "retry": "retry_step",
                "next": "next_step", 
                "finalize": "finalize"
            }
        )
        
        workflow.add_edge("retry_step", "evaluate_step")
        workflow.add_edge("next_step", "evaluate_step")
        
        workflow.add_conditional_edges(
            "finalize",
            self.should_approve,
            {
                "approve": "approve_prompt",
                "end": END
            }
        )
        
        workflow.add_edge("approve_prompt", END)
        
        return workflow.compile()

    async def load_prompt_data(self, state: EvaluationState) -> EvaluationState:
        """프롬프트 데이터 로드"""
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            0, 
            "loading", 
            f"프롬프트 카드 {state['card_id']} 데이터를 로드하고 있습니다..."
        )
        
        try:
            # AdminPromptCards에서 데이터 조회
            response = admin_cards_table.get_item(
                Key={
                    'PK': f"ADMIN#{state['admin_id']}",
                    'SK': f"CARD#{state['card_id']}#{state['version']}"
                }
            )
            
            if 'Item' not in response:
                raise ValueError(f"프롬프트 카드를 찾을 수 없습니다: {state['card_id']}")
            
            item = response['Item']
            state.update({
                "title": item['title'],
                "content": item['content'],
                "category": item['category'],
                "scores": {},
                "feedback": {},
                "overall_passed": False,
                "retry_count": 0,
                "max_retries": 3
            })
            
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                0, 
                "loaded", 
                f"프롬프트 데이터 로드 완료: {state['title']}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"프롬프트 데이터 로드 실패: {str(e)}")
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                0, 
                "error", 
                f"데이터 로드 실패: {str(e)}"
            )
            raise

    async def load_step_configurations(self, state: EvaluationState) -> EvaluationState:
        """단계별 평가 설정 로드"""
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            0, 
            "configuring", 
            "평가 단계 설정을 로드하고 있습니다..."
        )
        
        try:
            # StepConfigurations에서 설정 조회
            response = step_config_table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={':pk': 'CONFIG#STEPS'}
            )
            
            if response.get('Items'):
                # DB에서 설정 로드
                configs = []
                for item in response['Items']:
                    configs.append({
                        'stepNumber': int(item['SK'].split('#')[1]),
                        'stepName': item['stepName'], 
                        'threshold': float(item['threshold']),
                        'evaluationPrompt': item['evaluationPrompt']
                    })
                configs.sort(key=lambda x: x['stepNumber'])
                state["step_configs"] = configs
            else:
                # 기본 설정 사용
                state["step_configs"] = self.default_steps
                await self.log_thought(
                    state["session_id"], 
                    state["card_id"], 
                    0, 
                    "config", 
                    "기본 평가 설정을 사용합니다."
                )
            
            state["current_step"] = 1
            
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                0, 
                "configured", 
                f"{len(state['step_configs'])}개 평가 단계가 설정되었습니다."
            )
            
            return state
            
        except Exception as e:
            logger.error(f"설정 로드 실패: {str(e)}")
            # 기본 설정으로 폴백
            state["step_configs"] = self.default_steps
            state["current_step"] = 1
            return state

    async def evaluate_current_step(self, state: EvaluationState) -> EvaluationState:
        """현재 단계 평가 실행"""
        current_step = state["current_step"]
        step_config = next((s for s in state["step_configs"] if s["stepNumber"] == current_step), None)
        
        if not step_config:
            raise ValueError(f"단계 {current_step} 설정을 찾을 수 없습니다.")
        
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            current_step, 
            "evaluating", 
            f"단계 {current_step}: {step_config['stepName']} 평가를 시작합니다..."
        )
        
        try:
            # LLM으로 평가 실행
            prompt = step_config["evaluationPrompt"].format(
                content=state["content"],
                title=state["title"],
                category=state["category"]
            )
            
            messages = [
                SystemMessage(content="당신은 프롬프트 품질 평가 전문가입니다. 정확하고 객관적인 평가를 제공해주세요."),
                HumanMessage(content=prompt)
            ]
            
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                current_step, 
                "thinking", 
                f"{step_config['stepName']} 평가 기준에 따라 분석하고 있습니다..."
            )
            
            response = await self.llm.ainvoke(messages)
            result_text = response.content
            
            # JSON 파싱
            try:
                result = json.loads(result_text)
                score = float(result.get("score", 0.0))
                feedback = result.get("feedback", "평가 피드백이 없습니다.")
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 기본값
                score = 0.5
                feedback = f"평가 응답 파싱 실패: {result_text[:200]}"
            
            # 점수를 0-1 범위로 제한
            score = max(0.0, min(1.0, score))
            
            # 결과 저장
            step_name = step_config["stepName"]
            state["scores"][step_name] = score
            state["feedback"][step_name] = feedback
            
            # 평가 결과 DB에 저장
            await self.save_evaluation_result(state, step_config, score, feedback)
            
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                current_step, 
                "evaluated", 
                f"{step_name} 평가 완료 - 점수: {score:.2f}, 임계값: {step_config['threshold']}"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"단계 {current_step} 평가 실패: {str(e)}")
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                current_step, 
                "error", 
                f"평가 실패: {str(e)}"
            )
            # 실패 시 낮은 점수 할당
            step_name = step_config["stepName"]
            state["scores"][step_name] = 0.0
            state["feedback"][step_name] = f"평가 중 오류 발생: {str(e)}"
            return state

    async def check_step_result(self, state: EvaluationState) -> EvaluationState:
        """단계 평가 결과 확인"""
        current_step = state["current_step"]
        step_config = next((s for s in state["step_configs"] if s["stepNumber"] == current_step), None)
        
        if not step_config:
            return state
        
        step_name = step_config["stepName"]
        score = state["scores"].get(step_name, 0.0)
        threshold = step_config["threshold"]
        
        passed = score >= threshold
        
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            current_step, 
            "checking", 
            f"결과 확인: 점수 {score:.2f} vs 임계값 {threshold} = {'통과' if passed else '실패'}"
        )
        
        return state

    def should_continue(self, state: EvaluationState) -> str:
        """다음 단계 결정"""
        current_step = state["current_step"]
        step_config = next((s for s in state["step_configs"] if s["stepNumber"] == current_step), None)
        
        if not step_config:
            return "finalize"
        
        step_name = step_config["stepName"]
        score = state["scores"].get(step_name, 0.0)
        threshold = step_config["threshold"]
        
        if score < threshold:
            if state["retry_count"] < state["max_retries"]:
                return "retry"
            else:
                return "finalize"  # 재시도 횟수 초과, 최종 처리
        else:
            # 다음 단계가 있는지 확인
            next_step = current_step + 1
            has_next = any(s["stepNumber"] == next_step for s in state["step_configs"])
            return "next" if has_next else "finalize"

    async def retry_current_step(self, state: EvaluationState) -> EvaluationState:
        """현재 단계 재시도"""
        state["retry_count"] += 1
        
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            state["current_step"], 
            "retrying", 
            f"단계 {state['current_step']} 재시도 ({state['retry_count']}/{state['max_retries']})"
        )
        
        return state

    async def move_to_next_step(self, state: EvaluationState) -> EvaluationState:
        """다음 단계로 이동"""
        state["current_step"] += 1
        state["retry_count"] = 0  # 재시도 카운터 리셋
        
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            state["current_step"], 
            "proceeding", 
            f"단계 {state['current_step']}로 진행합니다."
        )
        
        return state

    async def finalize_evaluation(self, state: EvaluationState) -> EvaluationState:
        """평가 최종화"""
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            state["current_step"], 
            "finalizing", 
            "전체 평가 결과를 종합하고 있습니다..."
        )
        
        # 전체 통과 여부 결정
        all_passed = True
        for step_config in state["step_configs"]:
            step_name = step_config["stepName"]
            score = state["scores"].get(step_name, 0.0)
            threshold = step_config["threshold"]
            if score < threshold:
                all_passed = False
                break
        
        state["overall_passed"] = all_passed
        
        # AdminPromptCards 상태 업데이트
        try:
            admin_cards_table.update_item(
                Key={
                    'PK': f"ADMIN#{state['admin_id']}",
                    'SK': f"CARD#{state['card_id']}#{state['version']}"
                },
                UpdateExpression="SET overallStatus = :status, GSI1PK = :gsi1pk, updatedAt = :updated",
                ExpressionAttributeValues={
                    ':status': 'passed' if all_passed else 'failed',
                    ':gsi1pk': f"ADMIN#{state['admin_id']}#STATUS#{'passed' if all_passed else 'failed'}",
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
        except Exception as e:
            logger.error(f"상태 업데이트 실패: {str(e)}")
        
        status_msg = "모든 평가 단계를 통과했습니다!" if all_passed else "일부 평가 단계에서 기준에 미달했습니다."
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            0, 
            "finalized", 
            f"평가 완료: {status_msg}"
        )
        
        return state

    def should_approve(self, state: EvaluationState) -> str:
        """승인 여부 결정"""
        return "approve" if state["overall_passed"] else "end"

    async def approve_to_library(self, state: EvaluationState) -> EvaluationState:
        """GlobalPromptLibrary에 승인된 프롬프트 추가"""
        await self.log_thought(
            state["session_id"], 
            state["card_id"], 
            0, 
            "approving", 
            "승인된 프롬프트를 글로벌 라이브러리에 추가하고 있습니다..."
        )
        
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # 전체 점수 계산
            avg_score = sum(state["scores"].values()) / len(state["scores"]) if state["scores"] else 0.0
            
            # GlobalPromptLibrary에 추가
            library_item = {
                'PK': 'GLOBAL#PROMPTS',
                'SK': f"CARD#{state['card_id']}#{timestamp}",
                'GSI1PK': f"CATEGORY#{state['category']}",
                'cardId': state['card_id'],
                'title': state['title'],
                'content': state['content'],
                'category': state['category'],
                'approvedBy': state['admin_id'],
                'approvedAt': timestamp,
                'finalScore': Decimal(str(round(avg_score, 3))),
                'evaluationScores': {k: Decimal(str(round(v, 3))) for k, v in state['scores'].items()},
                'evaluationFeedback': state['feedback']
            }
            
            global_library_table.put_item(Item=library_item)
            
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                0, 
                "approved", 
                f"프롬프트가 글로벌 라이브러리에 승인되었습니다. (최종 점수: {avg_score:.2f})"
            )
            
        except Exception as e:
            logger.error(f"라이브러리 승인 실패: {str(e)}")
            await self.log_thought(
                state["session_id"], 
                state["card_id"], 
                0, 
                "error", 
                f"승인 처리 실패: {str(e)}"
            )
        
        return state

    async def save_evaluation_result(self, state: EvaluationState, step_config: Dict[str, Any], 
                                   score: float, feedback: str) -> None:
        """평가 결과를 PromptEvaluations 테이블에 저장"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            
            evaluation_item = {
                'PK': f"CARD#{state['card_id']}#{state['version']}",
                'SK': f"STEP#{step_config['stepNumber']}#EVAL#{timestamp}",
                'stepName': step_config['stepName'],
                'stepNumber': step_config['stepNumber'],
                'evaluationScore': Decimal(str(round(score, 3))),
                'threshold': Decimal(str(step_config['threshold'])),
                'passed': score >= step_config['threshold'],
                'feedback': feedback,
                'retryCount': state['retry_count'],
                'timestamp': timestamp,
                'sessionId': state['session_id']
            }
            
            evaluations_table.put_item(Item=evaluation_item)
            
        except Exception as e:
            logger.error(f"평가 결과 저장 실패: {str(e)}")

    async def log_thought(self, session_id: str, card_id: str, step_number: int, 
                         thought_type: str, content: str) -> None:
        """에이전트 사고 과정 로깅"""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            sequence = str(int(datetime.now(timezone.utc).timestamp() * 1000))
            
            # TTL: 30일 후 자동 삭제
            ttl = int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 60 * 60)
            
            thought_item = {
                'PK': f'SESSION#{session_id}',
                'SK': f'THOUGHT#{timestamp}#{sequence}',
                'cardId': card_id,
                'stepNumber': step_number,
                'thoughtType': thought_type,
                'content': content,
                'timestamp': timestamp,
                'ttl': ttl
            }
            
            thoughts_table.put_item(Item=thought_item)
            logger.info(f"Thought logged: {thought_type} - {content[:50]}...")
            
        except Exception as e:
            logger.error(f"사고 로깅 실패: {str(e)}")

# 워크플로우 인스턴스
workflow_manager = PromptEvaluationWorkflow()
evaluation_workflow = workflow_manager.create_workflow()

async def handler(event, context):
    """
    프롬프트 평가 워크플로우 실행 핸들러
    
    입력:
    {
        "cardId": "uuid",
        "version": "v123456789", 
        "adminId": "admin-cognito-sub",
        "sessionId": "evaluation-session-uuid"
    }
    """
    logger.info(f"Evaluation workflow started: {event}")
    
    try:
        # 초기 상태 구성
        initial_state: EvaluationState = {
            "card_id": event["cardId"],
            "version": event["version"],
            "admin_id": event["adminId"], 
            "session_id": event["sessionId"],
            "current_step": 1,
            "title": "",
            "content": "",
            "category": "",
            "scores": {},
            "feedback": {},
            "overall_passed": False,
            "retry_count": 0,
            "max_retries": 3,
            "step_configs": []
        }
        
        # 워크플로우 실행
        final_state = await evaluation_workflow.ainvoke(initial_state)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'cardId': final_state['card_id'],
                'overallPassed': final_state['overall_passed'],
                'scores': {k: float(v) for k, v in final_state['scores'].items()},
                'feedback': final_state['feedback'],
                'sessionId': final_state['session_id']
            })
        }
        
    except Exception as e:
        logger.error(f"Evaluation workflow failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }