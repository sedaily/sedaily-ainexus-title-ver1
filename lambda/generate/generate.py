import json
import boto3
import os
import logging
from datetime import datetime
from typing import Dict, Any
import urllib.parse

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
stepfunctions_client = boto3.client('stepfunctions', region_name=os.environ['REGION'])
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])

# 환경 변수
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']
REGION = os.environ['REGION']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions 실행 및 상태 조회 메인 핸들러
    
    - POST /projects/{id}/generate: Step Functions 실행
    - GET /executions/{arn}: 실행 상태 조회
    """
    try:
        logger.info(f"요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'POST':
            return start_step_functions_execution(event)
        elif http_method == 'GET':
            return get_execution_status(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"요청 처리 중 오류 발생: {str(e)}")
        return create_error_response(500, f"내부 서버 오류: {str(e)}")

def start_step_functions_execution(event: Dict[str, Any]) -> Dict[str, Any]:
    """Step Functions 실행 시작"""
    try:
        # 요청 데이터 파싱
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        article_text = body.get('article', '').strip()
        
        if not article_text:
            return create_error_response(400, "기사 내용이 필요합니다")
        
        if len(article_text) < 100:
            return create_error_response(400, "기사 내용이 너무 짧습니다 (최소 100자)")
        
        # Step Functions 실행
        execution_input = {
            'projectId': project_id,
            'article': article_text
        }
        
        execution_name = f"title-gen-{project_id}-{int(datetime.utcnow().timestamp())}"
        
        response = stepfunctions_client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps(execution_input)
        )
        
        execution_arn = response['executionArn']
        
        logger.info(f"Step Functions 실행 시작: {execution_arn}")
        
        return {
            'statusCode': 202,  # Accepted
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '제목 생성이 시작되었습니다',
                'executionArn': execution_arn,
                'executionName': execution_name,
                'projectId': project_id,
                'pollUrl': f"/executions/{urllib.parse.quote(execution_arn, safe='')}",
                'startTime': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"Step Functions 실행 실패: {str(e)}")
        return create_error_response(500, f"Step Functions 실행 실패: {str(e)}")

def get_execution_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Step Functions 실행 상태 조회"""
    try:
        # URL에서 execution ARN 파싱
        execution_arn = urllib.parse.unquote(event['pathParameters']['executionArn'])
        
        # Step Functions 실행 상태 조회
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        status = response['status']
        
        result = {
            'executionArn': execution_arn,
            'status': status,
            'startDate': response.get('startDate', '').isoformat() if response.get('startDate') else '',
            'stopDate': response.get('stopDate', '').isoformat() if response.get('stopDate') else '',
        }
        
        # 실행 완료된 경우 결과 조회
        if status == 'SUCCEEDED':
            result.update(get_execution_result(execution_arn))
        elif status == 'FAILED':
            result.update(get_execution_error(execution_arn))
        elif status == 'TIMED_OUT':
            result['error'] = '실행 시간이 초과되었습니다'
        elif status == 'ABORTED':
            result['error'] = '실행이 중단되었습니다'
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"실행 상태 조회 실패: {str(e)}")
        return create_error_response(500, f"실행 상태 조회 실패: {str(e)}")

def get_execution_result(execution_arn: str) -> Dict[str, Any]:
    """실행 완료 결과 조회"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        
        response = table.get_item(
            Key={'executionArn': execution_arn}
        )
        
        if 'Item' in response:
            item = response['Item']
            return {
                'conversationId': item.get('conversationId', ''),
                'projectId': item.get('projectId', ''),
                'result': item.get('result', {}),
                'usage': item.get('usage', {}),
                'completedAt': item.get('completedAt', '')
            }
        else:
            # DynamoDB에서 찾을 수 없는 경우 Step Functions에서 직접 조회
            return get_result_from_step_functions(execution_arn)
            
    except Exception as e:
        logger.error(f"실행 결과 조회 실패: {str(e)}")
        return {'error': f'결과 조회 실패: {str(e)}'}

def get_execution_error(execution_arn: str) -> Dict[str, Any]:
    """실행 실패 오류 조회"""
    try:
        table = dynamodb.Table(EXECUTION_TABLE)
        
        response = table.get_item(
            Key={'executionArn': execution_arn}
        )
        
        if 'Item' in response:
            item = response['Item']
            return {
                'error': item.get('error', {}),
                'failedAt': item.get('failedAt', '')
            }
        else:
            # DynamoDB에서 찾을 수 없는 경우 Step Functions에서 직접 조회
            return get_error_from_step_functions(execution_arn)
            
    except Exception as e:
        logger.error(f"실행 오류 조회 실패: {str(e)}")
        return {'error': f'오류 조회 실패: {str(e)}'}

def get_result_from_step_functions(execution_arn: str) -> Dict[str, Any]:
    """Step Functions에서 직접 결과 조회"""
    try:
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        if 'output' in response:
            output = json.loads(response['output'])
            return {
                'result': output.get('result', {}),
                'usage': output.get('usage', {}),
                'completedAt': response.get('stopDate', '').isoformat() if response.get('stopDate') else ''
            }
        
        return {'error': '결과를 찾을 수 없습니다'}
        
    except Exception as e:
        logger.error(f"Step Functions 결과 조회 실패: {str(e)}")
        return {'error': f'Step Functions 결과 조회 실패: {str(e)}'}

def get_error_from_step_functions(execution_arn: str) -> Dict[str, Any]:
    """Step Functions에서 직접 오류 조회"""
    try:
        response = stepfunctions_client.describe_execution(
            executionArn=execution_arn
        )
        
        error_info = {
            'type': 'EXECUTION_FAILED',
            'message': '실행이 실패했습니다',
            'failedAt': response.get('stopDate', '').isoformat() if response.get('stopDate') else ''
        }
        
        return {'error': error_info}
        
    except Exception as e:
        logger.error(f"Step Functions 오류 조회 실패: {str(e)}")
        return {'error': f'Step Functions 오류 조회 실패: {str(e)}'}

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False)
    } 