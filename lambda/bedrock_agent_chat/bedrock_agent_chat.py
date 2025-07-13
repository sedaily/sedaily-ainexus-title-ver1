import json
import boto3
import os
import uuid
import logging
import sys
from datetime import datetime

# ������ ������������ ���������
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../shared")
from common_utils import get_cors_headers, create_success_response, create_error_response, DecimalEncoder

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS ��������������� ���������
dynamodb = boto3.resource("dynamodb", region_name=os.environ["REGION"])
bedrock_agent = boto3.client("bedrock-agent-runtime", region_name=os.environ["REGION"])

# ������ ������
PROJECT_TABLE = os.environ["PROJECT_TABLE"]
CHAT_SESSION_TABLE = os.environ["CHAT_SESSION_TABLE"]
BEDROCK_AGENT_ID = os.environ["BEDROCK_AGENT_ID"]
BEDROCK_AGENT_ALIAS_ID = os.environ["BEDROCK_AGENT_ALIAS_ID"]
REGION = os.environ["REGION"]

def handler(event, context):
    """Bedrock Agent ������ ������ ���������"""
    try:
        logger.info(f"Bedrock Agent ������ ������ ������: {json.dumps(event, indent=2)}")
        
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": get_cors_headers(),
                "body": ""
            }
        elif http_method == "POST" and "/agent-chat" in path and "/sessions" not in path:
            return handle_agent_chat_message(event)
        elif http_method == "GET" and "/sessions" in path:
            if event.get("pathParameters", {}).get("sessionId"):
                return get_agent_chat_history(event)
            else:
                return get_agent_chat_sessions(event)
        elif http_method == "DELETE" and "/sessions" in path:
            return delete_agent_chat_session(event)
        else:
            return create_error_response(405, "������������ ������ ������������������")
            
    except Exception as e:
        logger.error(f"Bedrock Agent ������ ������ ������ ��� ������ ������: {str(e)}")
        return create_error_response(500, f"������ ������ ������: {str(e)}")

def handle_agent_chat_message(event):
    """Bedrock Agent ������ ��������� ������"""
    try:
        project_id = event["pathParameters"]["projectId"]
        body = json.loads(event["body"]) if event.get("body") else {}
        
        user_message = body.get("message", "").strip()
        session_id = body.get("sessionId") or str(uuid.uuid4())
        user_id = body.get("userId", "default")
        
        if not user_message:
            return create_error_response(400, "������������ ���������������")
        
        # Bedrock Agent ������
        response = bedrock_agent.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_message
        )
        
        # ������ ������
        agent_response = ""
        for event_stream in response["completion"]:
            if "chunk" in event_stream:
                chunk = event_stream["chunk"]
                if "bytes" in chunk:
                    agent_response += chunk["bytes"].decode("utf-8")
        
        return create_success_response({
            "sessionId": session_id,
            "projectId": project_id,
            "message": agent_response,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {"agentResponse": True}
        })
        
    except Exception as e:
        logger.error(f"Bedrock Agent ��������� ������ ������: {str(e)}")
        return create_error_response(500, f"������ ������ ������: {str(e)}")

def get_agent_chat_sessions(event):
    """Agent ������ ������ ������ ������"""
    try:
        project_id = event["pathParameters"]["projectId"]
        
        return create_success_response({
            "projectId": project_id,
            "sessions": []  # ��������� ������
        })
        
    except Exception as e:
        logger.error(f"Agent ������ ������ ������ ������ ������: {str(e)}")
        return create_error_response(500, f"������ ������ ������ ������: {str(e)}")

def get_agent_chat_history(event):
    """Agent ������ ������������ ������"""
    try:
        project_id = event["pathParameters"]["projectId"]
        session_id = event["pathParameters"]["sessionId"]
        
        return create_success_response({
            "projectId": project_id,
            "sessionId": session_id,
            "messages": []
        })
        
    except Exception as e:
        logger.error(f"Agent ������ ������������ ������ ������: {str(e)}")
        return create_error_response(500, f"������������ ������ ������: {str(e)}")

def delete_agent_chat_session(event):
    """Agent ������ ������ ������"""
    try:
        project_id = event["pathParameters"]["projectId"]
        session_id = event["pathParameters"]["sessionId"]
        
        return create_success_response({
            "message": "��������� ���������������������",
            "projectId": project_id,
            "sessionId": session_id
        })
        
    except Exception as e:
        logger.error(f"Agent ������ ������ ������: {str(e)}")
        return create_error_response(500, f"������ ������ ������: {str(e)}")

