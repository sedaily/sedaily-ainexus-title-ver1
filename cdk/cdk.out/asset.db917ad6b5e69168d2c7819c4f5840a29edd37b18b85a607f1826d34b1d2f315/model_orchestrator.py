"""
모델 오케스트레이션 시스템
- 작업별 최적 모델 선택  
- 비용 효율성 최적화
- 동적 라우팅
"""

import json
import boto3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ModelOrchestrator:
    """단계별 최적 모델 사용을 위한 오케스트레이터"""
    
    def __init__(self, region: str = 'us-east-1'):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        
        # 비용 효율성 기반 모델 계층
        self.models = {
            # 초경량: 전처리, 필터링 (가장 저렴)
            "ultra_light": "us.meta.llama3-2-1b-instruct-v1:0",
            
            # 경량: 키워드 추출, 분류
            "light": "us.meta.llama3-2-3b-instruct-v1:0", 
            
            # 균형: 요약, 구조화
            "balanced": "anthropic.claude-3-5-haiku-20241022-v1:0",
            
            # 고성능: 분석, 추론
            "high_performance": "us.meta.llama3-3-70b-instruct-v1:0",
            
            # 최고급: 창의적 생성
            "premium": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            
            # 초고급: 최고 품질 (필요시에만)
            "ultra_premium": "anthropic.claude-3-7-sonnet-20250109-v1:0"
        }
        
        # 작업별 모델 매핑
        self.task_model_map = {
            "preprocess": "ultra_light",      # 텍스트 전처리
            "extract_keywords": "light",      # 키워드 추출
            "summarize": "balanced",          # 요약
            "analyze": "high_performance",    # 분석
            "generate_creative": "premium",   # 창의적 생성
            "quality_check": "light",         # 품질 검사
            "final_polish": "ultra_premium"   # 최종 다듬기 (필요시만)
        }
        
        # 모델별 토큰 한계
        self.model_limits = {
            "ultra_light": {"max_tokens": 2048, "temperature": 0.3},
            "light": {"max_tokens": 2048, "temperature": 0.5},
            "balanced": {"max_tokens": 4096, "temperature": 0.6},
            "high_performance": {"max_tokens": 4096, "temperature": 0.7},
            "premium": {"max_tokens": 8192, "temperature": 0.7},
            "ultra_premium": {"max_tokens": 8192, "temperature": 0.8}
        }
    
    def choose_model_for_task(self, task: str, content_length: int = 0) -> str:
        """작업과 내용 길이에 따른 최적 모델 선택"""
        
        # 기본 모델 선택
        base_model = self.task_model_map.get(task, "balanced")
        
        # 내용 길이에 따른 조정
        if content_length > 5000:
            # 긴 텍스트: 더 강력한 모델 필요
            if base_model == "ultra_light":
                base_model = "light"
            elif base_model == "light":
                base_model = "balanced"
            elif base_model == "balanced":
                base_model = "high_performance"
        elif content_length < 500:
            # 짧은 텍스트: 경량 모델로 충분
            if base_model == "premium":
                base_model = "high_performance"
            elif base_model == "high_performance":
                base_model = "balanced"
        
        return self.models[base_model]
    
    def invoke_model(self, 
                    task: str, 
                    system_prompt: str, 
                    user_prompt: str, 
                    content_length: int = 0,
                    fallback: bool = True) -> Dict[str, Any]:
        """모델 호출 (자동 최적화 및 폴백 포함)"""
        
        model_id = self.choose_model_for_task(task, content_length)
        model_tier = self._get_model_tier(model_id)
        config = self.model_limits[model_tier]
        
        try:
            # 기본 모델로 시도
            result = self._call_bedrock(
                model_id=model_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=config["max_tokens"],
                temperature=config["temperature"]
            )
            
            logger.info(f"모델 호출 성공: {model_id} (task: {task})")
            return {
                "success": True,
                "content": result,
                "model_used": model_id,
                "task": task,
                "cost_tier": model_tier
            }
            
        except Exception as e:
            logger.warning(f"모델 호출 실패: {model_id}, 오류: {str(e)}")
            
            if fallback:
                # 폴백 전략: 한 단계 위 모델로 재시도
                fallback_model = self._get_fallback_model(model_tier)
                if fallback_model:
                    try:
                        fallback_result = self._call_bedrock(
                            model_id=fallback_model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            max_tokens=self.model_limits[self._get_model_tier(fallback_model)]["max_tokens"],
                            temperature=self.model_limits[self._get_model_tier(fallback_model)]["temperature"]
                        )
                        
                        logger.info(f"폴백 모델 호출 성공: {fallback_model}")
                        return {
                            "success": True,
                            "content": fallback_result,
                            "model_used": fallback_model,
                            "task": task,
                            "cost_tier": self._get_model_tier(fallback_model),
                            "fallback_used": True
                        }
                    except Exception as fallback_error:
                        logger.error(f"폴백 모델도 실패: {fallback_model}, 오류: {str(fallback_error)}")
            
            return {
                "success": False,
                "error": str(e),
                "model_attempted": model_id,
                "task": task
            }
    
    def _call_bedrock(self, model_id: str, system_prompt: str, user_prompt: str, 
                     max_tokens: int, temperature: float) -> str:
        """실제 Bedrock 모델 호출"""
        
        if "anthropic" in model_id:
            # Claude 모델
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            }
        else:
            # Llama 모델
            payload = {
                "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>",
                "max_gen_len": max_tokens,
                "temperature": temperature
            }
        
        response = self.bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(payload),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        if "anthropic" in model_id:
            return response_body['content'][0]['text']
        else:
            return response_body['generation']
    
    def _get_model_tier(self, model_id: str) -> str:
        """모델 ID로부터 티어 찾기"""
        for tier, mid in self.models.items():
            if mid == model_id:
                return tier
        return "balanced"
    
    def _get_fallback_model(self, current_tier: str) -> Optional[str]:
        """현재 티어보다 한 단계 위 모델 반환"""
        tier_hierarchy = [
            "ultra_light", "light", "balanced", 
            "high_performance", "premium", "ultra_premium"
        ]
        
        try:
            current_index = tier_hierarchy.index(current_tier)
            if current_index < len(tier_hierarchy) - 1:
                next_tier = tier_hierarchy[current_index + 1]
                return self.models[next_tier]
        except ValueError:
            pass
        
        return None
    
    def estimate_cost(self, task: str, content_length: int) -> Dict[str, Any]:
        """작업별 예상 비용 계산"""
        model_id = self.choose_model_for_task(task, content_length)
        model_tier = self._get_model_tier(model_id)
        
        # 대략적인 토큰당 비용 (USD, 2024년 기준)
        cost_per_1k_tokens = {
            "ultra_light": 0.0001,    # Llama 3.2 1B
            "light": 0.0002,          # Llama 3.2 3B  
            "balanced": 0.0003,       # Claude 3.5 Haiku
            "high_performance": 0.001, # Llama 3.3 70B
            "premium": 0.003,         # Claude 3.5 Sonnet
            "ultra_premium": 0.010    # Claude 3.7 Sonnet
        }
        
        estimated_input_tokens = content_length // 4  # 대략적인 토큰 추정
        estimated_output_tokens = 200  # 평균 출력 토큰
        
        input_cost = (estimated_input_tokens / 1000) * cost_per_1k_tokens[model_tier]
        output_cost = (estimated_output_tokens / 1000) * cost_per_1k_tokens[model_tier] * 3  # 출력이 보통 3배 비쌈
        
        total_cost = input_cost + output_cost
        
        return {
            "model_id": model_id,
            "model_tier": model_tier,
            "estimated_cost_usd": round(total_cost, 6),
            "input_tokens": estimated_input_tokens,
            "output_tokens": estimated_output_tokens,
            "cost_breakdown": {
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6)
            }
        } 