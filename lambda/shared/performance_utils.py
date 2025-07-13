"""
성능 최적화 유틸리티
- Lambda 메모리 캐싱
- CloudWatch 메트릭 전송
- 오류 처리 최적화
"""

import json
import time
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# 글로벌 캐시 (Lambda 컨테이너 재사용)
_cache = {}
_cache_stats = {'hits': 0, 'misses': 0}

def performance_monitor(operation_name: str):
    """성능 모니터링 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # milliseconds
                
                # 성공 메트릭 전송
                send_performance_metric(operation_name, duration, True)
                
                logger.info(f"{operation_name} 완료: {duration:.2f}ms")
                return result
                
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                
                # 실패 메트릭 전송
                send_performance_metric(operation_name, duration, False)
                
                logger.error(f"{operation_name} 실패: {duration:.2f}ms, 오류: {str(e)}")
                raise
                
        return wrapper
    return decorator

def cache_get(key: str) -> Optional[Any]:
    """메모리 캐시에서 값 조회"""
    if key in _cache:
        _cache_stats['hits'] += 1
        entry = _cache[key]
        
        # TTL 체크 (5분)
        if time.time() - entry['timestamp'] < 300:
            return entry['data']
        else:
            del _cache[key]
    
    _cache_stats['misses'] += 1
    return None

def cache_set(key: str, data: Any, ttl: int = 300):
    """메모리 캐시에 값 저장"""
    # 캐시 크기 제한 (100개)
    if len(_cache) >= 100:
        # LRU: 가장 오래된 항목 제거
        oldest_key = min(_cache.keys(), key=lambda k: _cache[k]['timestamp'])
        del _cache[oldest_key]
    
    _cache[key] = {
        'data': data,
        'timestamp': time.time()
    }

def get_cache_stats() -> Dict[str, Any]:
    """캐시 통계 반환"""
    total = _cache_stats['hits'] + _cache_stats['misses']
    hit_rate = _cache_stats['hits'] / total if total > 0 else 0
    
    return {
        'hit_rate': hit_rate,
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'cache_size': len(_cache)
    }

def send_performance_metric(operation: str, duration: float, success: bool):
    """CloudWatch 성능 메트릭 전송"""
    try:
        cloudwatch = boto3.client('cloudwatch')
        
        metrics = [
            {
                'MetricName': f'{operation}_Duration',
                'Value': duration,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Operation', 'Value': operation},
                    {'Name': 'Success', 'Value': str(success)}
                ]
            },
            {
                'MetricName': f'{operation}_Count',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Operation', 'Value': operation},
                    {'Name': 'Success', 'Value': str(success)}
                ]
            }
        ]
        
        cloudwatch.put_metric_data(
            Namespace='TITLE-NOMICS/Performance',
            MetricData=metrics
        )
        
    except Exception as e:
        logger.warning(f"메트릭 전송 실패: {str(e)}")

def optimize_bedrock_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Bedrock 페이로드 최적화"""
    # 토큰 수 추정 및 제한
    estimated_tokens = estimate_tokens(str(payload))
    
    if estimated_tokens > 8000:  # 안전 마진
        # 메시지 내용 압축
        if 'messages' in payload:
            for message in payload['messages']:
                if len(message['content']) > 5000:
                    message['content'] = message['content'][:5000] + "...[생략]"
        
        # 시스템 프롬프트 압축
        if 'system' in payload and len(payload['system']) > 3000:
            payload['system'] = payload['system'][:3000] + "...[생략]"
    
    return payload

def estimate_tokens(text: str) -> int:
    """토큰 수 대략 추정 (1토큰 ≈ 4문자)"""
    return len(text) // 4

class BatchProcessor:
    """배치 처리 최적화"""
    
    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size
        self.batch = []
    
    def add(self, item: Any):
        """배치에 아이템 추가"""
        self.batch.append(item)
        
        if len(self.batch) >= self.batch_size:
            return self.process_batch()
        
        return None
    
    def process_batch(self) -> list:
        """배치 처리 및 초기화"""
        if not self.batch:
            return []
        
        # 실제 배치 처리 로직 (하위 클래스에서 구현)
        results = self._process_items(self.batch)
        self.batch.clear()
        return results
    
    def _process_items(self, items: list) -> list:
        """하위 클래스에서 구현"""
        return items
    
    def flush(self) -> list:
        """남은 배치 강제 처리"""
        return self.process_batch()

def create_error_response(status_code: int, message: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """표준화된 오류 응답 생성"""
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps({
            'error': {
                'message': message,
                'code': status_code,
                'timestamp': datetime.utcnow().isoformat()
            },
            'details': details or {}
        }, ensure_ascii=False)
    }
    
    # 오류 메트릭 전송
    send_performance_metric('error_response', 0, False)
    
    return response

def validate_input(data: Dict[str, Any], required_fields: list) -> Optional[str]:
    """입력 데이터 검증"""
    for field in required_fields:
        if field not in data or not data[field]:
            return f"필수 필드 누락: {field}"
    
    return None