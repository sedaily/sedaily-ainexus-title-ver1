"""
AI 대화 생성 Lambda 함수
- 단순하고 효율적인 구조
- 모델 오케스트레이션 기반 비용 최적화
- 사용자 프롬프트 카드 기반 동적 처리
"""

import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import urllib.parse

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 새로운 모듈들 임포트
from model_orchestrator import ModelOrchestrator
from prompt_manager import SimplePromptManager

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE', '')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET', '')
REGION = os.environ['REGION']

# CORS 헤더
def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """메인 핸들러 - 단순화된 구조"""
    
    try:
        # HTTP 메서드 확인
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # 요청 본문 파싱
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # 필수 파라미터 확인
        project_id = body.get('projectId')
        user_input = body.get('userInput', '').strip()
        
        if not project_id:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '프로젝트 ID가 필요합니다.',
                    'error': 'projectId is required'
                }, ensure_ascii=False)
            }
        
        if not user_input:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '사용자 입력이 필요합니다.',
                    'error': 'userInput is required'
                }, ensure_ascii=False)
            }
        
        # 길이 체크 (최소 길이 완화)
        if len(user_input) < 10:
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '더 자세한 내용을 입력해주세요',
                    'result': f'현재 입력하신 내용이 {len(user_input)}자입니다.\n\n더 정확한 결과를 위해 조금 더 구체적인 내용을 입력해주세요.',
                    'projectId': project_id,
                    'mode': 'guidance',
                    'timestamp': datetime.utcnow().isoformat(),
                    'input_length': len(user_input)
                }, ensure_ascii=False)
            }
        
        # 모델 오케스트레이터 및 프롬프트 매니저 초기화
        orchestrator = ModelOrchestrator(region=REGION)
        prompt_manager = SimplePromptManager(
            prompt_bucket=PROMPT_BUCKET,
            prompt_meta_table=PROMPT_META_TABLE,
            region=REGION
        )
        
        # 프롬프트 카드 로드
        prompts = prompt_manager.load_project_prompts(project_id)
        
        # 프롬프트 유효성 검사
        validation = prompt_manager.validate_prompts(prompts)
        
        if not validation['valid']:
            # 프롬프트가 없거나 유효하지 않은 경우 - 순수 베드락 모델과 대화
            return handle_direct_conversation(orchestrator, user_input, project_id)
        
        # 프롬프트 카드가 있는 경우 - 프롬프트 기반 처리
        return handle_prompt_based_conversation(
            orchestrator, prompt_manager, prompts, user_input, project_id
        )
        
    except Exception as e:
        logger.error(f"핸들러 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '서버 오류가 발생했습니다.',
                'error': str(e)
            }, ensure_ascii=False)
        }
        
def handle_direct_conversation(orchestrator: ModelOrchestrator, user_input: str, project_id: str) -> Dict[str, Any]:
    """순수 베드락 모델과의 직접 대화 (프롬프트 카드 없음)"""
    
    try:
        logger.info(f"순수 베드락 대화 시작 (프로젝트: {project_id})")
        
        # 빈 시스템 프롬프트로 순수 대화
        result = orchestrator.invoke_model(
            task="generate_creative",  # 창의적 대화 생성
            system_prompt="",  # 완전히 빈 시스템 프롬프트
            user_prompt=user_input,
            content_length=len(user_input)
        )
        
        if result['success']:
                    return {
                        'statusCode': 200,
                        'headers': get_cors_headers(),
                        'body': json.dumps({
                    'message': '응답이 생성되었습니다.',
                    'result': result['content'],
                            'projectId': project_id,
                    'mode': 'direct_conversation',
                    'model_info': {
                        'model_used': result['model_used'],
                        'cost_tier': result['cost_tier'],
                        'fallback_used': result.get('fallback_used', False)
                    },
                            'timestamp': datetime.utcnow().isoformat(),
                    'input_length': len(user_input),
                    'output_length': len(result['content'])
                        }, ensure_ascii=False)
                    }
            else:
        return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '응답 생성 중 오류가 발생했습니다.',
                    'error': result.get('error', 'Unknown error'),
                    'projectId': project_id
                }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"직접 대화 처리 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '대화 처리 중 오류가 발생했습니다.',
                'error': str(e)
            }, ensure_ascii=False)
        }

def handle_prompt_based_conversation(orchestrator: ModelOrchestrator, 
                                   prompt_manager: SimplePromptManager,
                                   prompts: List[Dict[str, Any]], 
                                   user_input: str, 
                                   project_id: str) -> Dict[str, Any]:
    """프롬프트 카드 기반 대화 처리"""
    
    try:
        logger.info(f"프롬프트 기반 대화 시작 (프로젝트: {project_id}, 프롬프트: {len(prompts)}개)")
        
        # 프롬프트들을 결합하여 시스템 프롬프트 생성
        system_prompt = prompt_manager.combine_prompts(prompts, mode="system")
        
        # 프롬프트 통계
        stats = prompt_manager.get_project_prompt_stats(project_id)
        
        # 적절한 작업 유형 결정 (프롬프트 길이와 내용에 따라)
        task_type = determine_task_type(system_prompt, user_input)
        
        # 모델 호출
        result = orchestrator.invoke_model(
            task=task_type,
            system_prompt=system_prompt,
            user_prompt=user_input,
            content_length=len(system_prompt) + len(user_input)
        )
        
        if result['success']:
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '응답이 생성되었습니다.',
                    'result': result['content'],
                    'projectId': project_id,
                    'mode': 'prompt_based',
                    'prompt_stats': {
                        'total_prompts': len(prompts),
                        'total_prompt_length': len(system_prompt),
                        'average_prompt_length': stats.get('average_length', 0)
                    },
                    'model_info': {
                        'model_used': result['model_used'],
                        'cost_tier': result['cost_tier'],
                        'task_type': task_type,
                        'fallback_used': result.get('fallback_used', False)
                    },
                    'timestamp': datetime.utcnow().isoformat(),
                    'input_length': len(user_input),
                    'output_length': len(result['content'])
                }, ensure_ascii=False)
            }
        else:
            return {
                'statusCode': 500,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': '응답 생성 중 오류가 발생했습니다.',
                    'error': result.get('error', 'Unknown error'),
                    'projectId': project_id,
                    'model_attempted': result.get('model_attempted')
                }, ensure_ascii=False)
            }
        
    except Exception as e:
        logger.error(f"프롬프트 기반 대화 처리 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '프롬프트 기반 처리 중 오류가 발생했습니다.',
                'error': str(e)
            }, ensure_ascii=False)
        }

def determine_task_type(system_prompt: str, user_input: str) -> str:
    """시스템 프롬프트와 사용자 입력을 분석하여 최적 작업 유형 결정"""
    
    prompt_lower = system_prompt.lower()
    input_lower = user_input.lower()
    
    # 키워드 기반 작업 유형 결정
    creative_keywords = ['창의', '아이디어', '제목', '스토리', '콘텐츠', '브레인스토밍']
    analytical_keywords = ['분석', '검토', '평가', '요약', '정리', '비교']
    summary_keywords = ['요약', '정리', '압축', '간단히', '핵심']
    
    # 길이 기반 판단
    if len(system_prompt) > 5000 or len(user_input) > 2000:
        return "analyze"  # 긴 텍스트는 분석 작업으로
    
    # 키워드 기반 판단
    if any(keyword in prompt_lower or keyword in input_lower for keyword in creative_keywords):
        return "generate_creative"
    elif any(keyword in prompt_lower or keyword in input_lower for keyword in analytical_keywords):
        return "analyze"
    elif any(keyword in prompt_lower or keyword in input_lower for keyword in summary_keywords):
        return "summarize"
    else:
        return "generate_creative"  # 기본값

# 실행 기록 저장 (선택적)
def save_execution_record(project_id: str, user_input: str, result: str, model_info: Dict[str, Any]) -> None:
    """실행 기록을 DynamoDB에 저장 (모니터링용)"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        
        record = {
            'executionId': f"{project_id}_{int(datetime.utcnow().timestamp() * 1000)}",
            'projectId': project_id,
            'timestamp': datetime.utcnow().isoformat(),
            'inputLength': len(user_input),
            'outputLength': len(result),
            'modelInfo': model_info,
            'status': 'completed'
        }
        
        table.put_item(Item=record)
        logger.info(f"실행 기록 저장 완료: {record['executionId']}")
        
    except Exception as e:
        logger.warning(f"실행 기록 저장 실패: {str(e)}")

# 기존의 복잡한 함수들은 모두 제거됨:
# - execute_step_with_prompts
# - generate_final_titles_from_steps  
# - search_prompts_by_step
# - search_prompts_by_step_fallback
# - generate_title_with_rag
# - create_bedrock_payload_orchestrated
# - create_bedrock_payload_direct
# - FAISS 관련 모든 로직 