import json
import boto3
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])

# 환경 변수
CONVERSATION_TABLE = os.environ['CONVERSATION_TABLE']
EXECUTION_TABLE = os.environ['EXECUTION_TABLE']
REGION = os.environ['REGION']

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Step Functions에서 호출되는 결과 저장 핸들러
    """
    try:
        logger.info(f"결과 저장 요청: {json.dumps(event, indent=2)}")
        
        project_id = event.get('projectId')
        article = event.get('article')
        result = event.get('result')
        usage = event.get('usage', {})
        execution_arn = event.get('executionArn')
        
        if not project_id:
            raise ValueError("projectId가 필요합니다")
        
        if not result:
            raise ValueError("결과가 필요합니다")
        
        # 대화 기록 저장
        conversation_id = save_conversation(project_id, article, result, usage, execution_arn)
        
        # 실행 결과 저장
        save_execution_result(execution_arn, project_id, conversation_id, result, usage)
        
        logger.info(f"결과 저장 완료: {conversation_id}")
        
        return {
            'statusCode': 200,
            'conversationId': conversation_id,
            'projectId': project_id,
            'executionArn': execution_arn,
            'result': result,
            'usage': usage,
            'timestamp': datetime.utcnow().isoformat(),
            'message': "Title generation completed successfully"
        }
        
    except Exception as e:
        logger.error(f"결과 저장 실패: {str(e)}")
        raise

def save_conversation(project_id: str, article: str, result: Dict[str, Any], usage: Dict[str, Any], execution_arn: str) -> str:
    """대화 기록 저장"""
    try:
        table = dynamodb.Table(CONVERSATION_TABLE)
        conversation_id = str(uuid.uuid4())
        timestamp = int(datetime.utcnow().timestamp() * 1000)  # 밀리초 단위
        
        # 결과에서 콘텐츠 추출
        content = ""
        if isinstance(result, dict):
            if 'content' in result:
                if isinstance(result['content'], list) and len(result['content']) > 0:
                    content = result['content'][0].get('text', '')
                else:
                    content = str(result['content'])
            else:
                content = json.dumps(result, ensure_ascii=False)
        else:
            content = str(result)
        
        table.put_item(
            Item={
                'projectId': project_id,
                'timestamp': timestamp,
                'conversationId': conversation_id,
                'articleText': article or '',
                'generatedContent': content,
                'modelId': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
                'usage': usage,
                'executionArn': execution_arn or '',
                'createdAt': datetime.utcnow().isoformat(),
                'articleLength': len(article) if article else 0,
                'status': 'completed'
            }
        )
        
        logger.info(f"대화 기록 저장 완료: {conversation_id}")
        return conversation_id
        
    except Exception as e:
        logger.error(f"대화 기록 저장 실패: {str(e)}")
        raise

def save_execution_result(execution_arn: str, project_id: str, conversation_id: str, result: Dict[str, Any], usage: Dict[str, Any]) -> None:
    """실행 결과 저장 (Step Functions 실행 결과 추적용)"""
    try:
        if not execution_arn:
            logger.warning("실행 ARN이 없어 실행 결과 저장을 건너뜁니다")
            return
        
        table = dynamodb.Table(EXECUTION_TABLE)
        
        # TTL 설정 (7일 후 자동 삭제)
        ttl = int(datetime.utcnow().timestamp()) + (7 * 24 * 60 * 60)
        
        table.put_item(
            Item={
                'executionArn': execution_arn,
                'projectId': project_id,
                'conversationId': conversation_id,
                'status': 'SUCCEEDED',
                'result': result,
                'usage': usage,
                'completedAt': datetime.utcnow().isoformat(),
                'ttl': ttl
            }
        )
        
        logger.info(f"실행 결과 저장 완료: {execution_arn}")
        
    except Exception as e:
        logger.error(f"실행 결과 저장 실패: {str(e)}")
        # 실행 결과 저장 실패해도 메인 프로세스는 계속 진행
        pass 