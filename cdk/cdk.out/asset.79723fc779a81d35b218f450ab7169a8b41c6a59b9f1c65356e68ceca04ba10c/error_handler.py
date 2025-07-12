import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
sns_client = boto3.client('sns', region_name=os.environ['REGION'])

# 환경 변수
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']
ERROR_TOPIC = os.environ['ERROR_TOPIC']
REGION = os.environ['REGION']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions에서 호출되는 오류 처리 핸들러
    """
    try:
        logger.info(f"오류 처리 요청: {json.dumps(event, indent=2)}")
        
        error = event.get('error', {})
        error_type = event.get('errorType', 'UNKNOWN')
        execution_arn = event.get('executionArn')
        project_id = event.get('projectId')
        
        # 오류 정보 추출
        error_info = extract_error_info(error, error_type)
        
        # 실행 결과에 오류 상태 저장
        save_error_result(execution_arn, project_id, error_info)
        
        # 중요한 오류의 경우 SNS 알림 발송
        if should_send_notification(error_info):
            send_error_notification(error_info, execution_arn, project_id)
        
        logger.info(f"오류 처리 완료: {error_type}")
        
        return {
            'statusCode': 200,
            'error': error_info,
            'executionArn': execution_arn,
            'projectId': project_id,
            'timestamp': datetime.utcnow().isoformat(),
            'message': "Error handled successfully"
        }
        
    except Exception as e:
        logger.error(f"오류 처리 실패: {str(e)}")
        # 오류 처리 자체가 실패해도 Step Functions는 계속 진행
        return {
            'statusCode': 500,
            'error': str(e),
            'message': "Error handling failed"
        }

def extract_error_info(error: Dict[str, Any], error_type: str) -> Dict[str, Any]:
    """오류 정보 추출 및 분류"""
    try:
        error_info = {
            'type': error_type,
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'MEDIUM'
        }
        
        if isinstance(error, dict):
            # Lambda 함수 오류
            if 'errorMessage' in error:
                error_info['message'] = error['errorMessage']
                error_info['details'] = error.get('errorType', '')
            
            # Bedrock 오류
            elif 'Error' in error:
                error_info['message'] = error.get('Error', '')
                error_info['details'] = error.get('Cause', '')
            
            # Guardrail 위반
            elif error_type == 'GUARDRAIL_VIOLATION':
                error_info['message'] = "콘텐츠가 가이드라인을 위반했습니다"
                error_info['severity'] = 'HIGH'
                error_info['details'] = json.dumps(error, ensure_ascii=False)
            
            # 기타 오류
            else:
                error_info['message'] = str(error)
                error_info['details'] = json.dumps(error, ensure_ascii=False)
        
        else:
            error_info['message'] = str(error)
        
        # 심각도 결정
        if error_type in ['GUARDRAIL_VIOLATION', 'TIMEOUT', 'RESOURCE_LIMIT']:
            error_info['severity'] = 'HIGH'
        elif error_type in ['VALIDATION_ERROR', 'PARSING_ERROR']:
            error_info['severity'] = 'LOW'
        
        return error_info
        
    except Exception as e:
        logger.error(f"오류 정보 추출 실패: {str(e)}")
        return {
            'type': 'UNKNOWN',
            'message': str(error),
            'severity': 'MEDIUM',
            'timestamp': datetime.utcnow().isoformat()
        }

def save_error_result(execution_arn: str, project_id: str, error_info: Dict[str, Any]) -> None:
    """실행 결과에 오류 상태 저장"""
    try:
        if not execution_arn:
            logger.warning("실행 ARN이 없어 오류 결과 저장을 건너뜁니다")
            return
        
        table = dynamodb.Table(EXECUTION_TABLE)
        
        # TTL 설정 (7일 후 자동 삭제)
        ttl = int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)
        
        table.put_item(
            Item={
                'executionArn': execution_arn,
                'projectId': project_id or '',
                'status': 'FAILED',
                'error': error_info,
                'failedAt': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )
        
        logger.info(f"오류 결과 저장 완료: {execution_arn}")
        
    except Exception as e:
        logger.error(f"오류 결과 저장 실패: {str(e)}")
        # 오류 결과 저장 실패해도 메인 프로세스는 계속 진행
        pass

def should_send_notification(error_info: Dict[str, Any]) -> bool:
    """SNS 알림 발송 여부 결정"""
    try:
        severity = error_info.get('severity', 'MEDIUM')
        error_type = error_info.get('type', 'UNKNOWN')
        
        # 심각도가 HIGH이거나 특정 오류 유형의 경우 알림 발송
        if severity == 'HIGH':
            return True
        
        if error_type in ['GUARDRAIL_VIOLATION', 'TIMEOUT', 'RESOURCE_LIMIT']:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"알림 발송 여부 결정 실패: {str(e)}")
        return False

def send_error_notification(error_info: Dict[str, Any], execution_arn: str, project_id: str) -> None:
    """SNS를 통한 오류 알림 발송"""
    try:
        message = {
            'title': '🚨 TITLE-NOMICS 오류 알림',
            'error_type': error_info.get('type', 'UNKNOWN'),
            'severity': error_info.get('severity', 'MEDIUM'),
            'message': error_info.get('message', ''),
            'project_id': project_id,
            'execution_arn': execution_arn,
            'timestamp': error_info.get('timestamp', ''),
            'details': error_info.get('details', '')
        }
        
        sns_client.publish(
            TopicArn=ERROR_TOPIC,
            Subject=f"TITLE-NOMICS 오류 알림: {error_info.get('type', 'UNKNOWN')}",
            Message=json.dumps(message, ensure_ascii=False, indent=2)
        )
        
        logger.info(f"오류 알림 발송 완료: {error_info.get('type', 'UNKNOWN')}")
        
    except Exception as e:
        logger.error(f"오류 알림 발송 실패: {str(e)}")
        # 알림 발송 실패해도 메인 프로세스는 계속 진행
        pass 