#!/usr/bin/env python3
"""
User Management API Lambda Function
Handles user profiles, subscriptions, and usage tracking
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Environment variables
USERS_TABLE_NAME = os.environ.get("USERS_TABLE_NAME")
USAGE_TABLE_NAME = os.environ.get("USAGE_TABLE_NAME")  
SUBSCRIPTIONS_TABLE_NAME = os.environ.get("SUBSCRIPTIONS_TABLE_NAME")
USER_POOL_ID = os.environ.get("USER_POOL_ID")

# AWS clients
dynamodb = boto3.resource("dynamodb")
cognito = boto3.client("cognito-idp")

# DynamoDB tables
users_table = dynamodb.Table(USERS_TABLE_NAME)
usage_table = dynamodb.Table(USAGE_TABLE_NAME)
subscriptions_table = dynamodb.Table(SUBSCRIPTIONS_TABLE_NAME)

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "api_calls_per_day": 10,
        "features": ["basic_chat"],
        "price": 0
    },
    "pro": {
        "name": "Pro", 
        "api_calls_per_day": 100,
        "features": ["basic_chat", "advanced_search", "history"],
        "price": 9.99
    },
    "enterprise": {
        "name": "Enterprise",
        "api_calls_per_day": 1000, 
        "features": ["basic_chat", "advanced_search", "history", "analytics", "priority_support"],
        "price": 29.99
    }
}


class UserManagementError(Exception):
    """Custom exception for user management errors"""
    pass


def json_response(status_code: int, body: Dict[str, Any], cors: bool = True) -> Dict[str, Any]:
    """Create standardized JSON response"""
    response = {
        "statusCode": status_code,
        "body": json.dumps(body, default=str, ensure_ascii=False)
    }
    
    if cors:
        response["headers"] = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    
    return response


def get_user_from_context(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract user information from authorizer context"""
    try:
        context = event.get("requestContext", {}).get("authorizer", {})
        
        user_id = context.get("userId")
        username = context.get("username", "")
        email = context.get("email", "")
        
        if not user_id:
            raise UserManagementError("Missing user ID in authorization context")
        
        return {
            "user_id": user_id,
            "username": username,
            "email": email
        }
    except Exception as e:
        logger.error(f"Failed to extract user from context: {str(e)}")
        raise UserManagementError("Invalid authorization context")


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile from DynamoDB"""
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        
        if "Item" in response:
            user_data = response["Item"]
            # Convert Decimal to float for JSON serialization
            return {k: float(v) if isinstance(v, Decimal) else v for k, v in user_data.items()}
        else:
            # Create default user profile if doesn't exist
            default_profile = {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "subscription_plan": "free",
                "status": "active"
            }
            
            users_table.put_item(Item=default_profile)
            return default_profile
            
    except ClientError as e:
        logger.error(f"DynamoDB error getting user profile: {str(e)}")
        raise UserManagementError(f"Failed to get user profile: {str(e)}")


def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update user profile in DynamoDB"""
    try:
        # Prepare update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {":updated_at": datetime.utcnow().isoformat()}
        expression_names = {}
        
        for key, value in updates.items():
            if key not in ["user_id", "created_at"]:  # Don't allow updating these fields
                placeholder = f":{key}"
                if key in ["status", "name"]:  # Reserved keywords need attribute names
                    attr_name = f"#{key}"
                    expression_names[attr_name] = key
                    update_expression += f", {attr_name} = {placeholder}"
                else:
                    update_expression += f", {key} = {placeholder}"
                expression_values[placeholder] = value
        
        # Update item
        kwargs = {
            "Key": {"user_id": user_id},
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
            "ReturnValues": "ALL_NEW"
        }
        
        if expression_names:
            kwargs["ExpressionAttributeNames"] = expression_names
        
        response = users_table.update_item(**kwargs)
        
        updated_item = response["Attributes"]
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in updated_item.items()}
        
    except ClientError as e:
        logger.error(f"DynamoDB error updating user profile: {str(e)}")
        raise UserManagementError(f"Failed to update user profile: {str(e)}")


def get_user_usage(user_id: str, days: int = 30) -> Dict[str, Any]:
    """Get user usage statistics"""
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Query usage data
        response = usage_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id) &
                                  boto3.dynamodb.conditions.Key("date").between(
                                      start_date.isoformat(),
                                      end_date.isoformat()
                                  )
        )
        
        usage_data = response.get("Items", [])
        
        # Calculate totals
        total_api_calls = sum(int(item.get("api_calls", 0)) for item in usage_data)
        total_tokens = sum(int(item.get("tokens_used", 0)) for item in usage_data)
        
        # Get today's usage
        today = end_date.isoformat()
        today_usage = next((item for item in usage_data if item.get("date") == today), {})
        
        return {
            "period": f"{days} days",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_api_calls": total_api_calls,
            "total_tokens": total_tokens,
            "today": {
                "api_calls": int(today_usage.get("api_calls", 0)),
                "tokens_used": int(today_usage.get("tokens_used", 0))
            },
            "daily_data": [
                {
                    "date": item.get("date"),
                    "api_calls": int(item.get("api_calls", 0)),
                    "tokens_used": int(item.get("tokens_used", 0))
                }
                for item in sorted(usage_data, key=lambda x: x.get("date", ""))
            ]
        }
        
    except ClientError as e:
        logger.error(f"DynamoDB error getting usage: {str(e)}")
        raise UserManagementError(f"Failed to get usage data: {str(e)}")


def get_user_subscription(user_id: str) -> Dict[str, Any]:
    """Get user subscription information"""
    try:
        response = subscriptions_table.get_item(Key={"user_id": user_id})
        
        if "Item" in response:
            subscription = response["Item"]
            plan_type = subscription.get("plan_type", "free")
            
            # Convert Decimal to appropriate types
            subscription_data = {k: float(v) if isinstance(v, Decimal) else v for k, v in subscription.items()}
            
            # Add plan details
            subscription_data["plan_details"] = SUBSCRIPTION_PLANS.get(plan_type, SUBSCRIPTION_PLANS["free"])
            
            return subscription_data
        else:
            # Create default free subscription
            default_subscription = {
                "user_id": user_id,
                "plan_type": "free",
                "status": "active",
                "start_date": datetime.utcnow().date().isoformat(),
                "created_at": datetime.utcnow().isoformat()
            }
            
            subscriptions_table.put_item(Item=default_subscription)
            default_subscription["plan_details"] = SUBSCRIPTION_PLANS["free"]
            
            return default_subscription
            
    except ClientError as e:
        logger.error(f"DynamoDB error getting subscription: {str(e)}")
        raise UserManagementError(f"Failed to get subscription: {str(e)}")


def update_user_subscription(user_id: str, plan_type: str) -> Dict[str, Any]:
    """Update user subscription plan"""
    try:
        if plan_type not in SUBSCRIPTION_PLANS:
            raise UserManagementError(f"Invalid plan type: {plan_type}")
        
        # Update subscription
        response = subscriptions_table.update_item(
            Key={"user_id": user_id},
            UpdateExpression="SET plan_type = :plan, updated_at = :updated",
            ExpressionAttributeValues={
                ":plan": plan_type,
                ":updated": datetime.utcnow().isoformat()
            },
            ReturnValues="ALL_NEW"
        )
        
        subscription_data = response["Attributes"]
        subscription_data = {k: float(v) if isinstance(v, Decimal) else v for k, v in subscription_data.items()}
        subscription_data["plan_details"] = SUBSCRIPTION_PLANS[plan_type]
        
        # Also update user profile
        update_user_profile(user_id, {"subscription_plan": plan_type})
        
        return subscription_data
        
    except ClientError as e:
        logger.error(f"DynamoDB error updating subscription: {str(e)}")
        raise UserManagementError(f"Failed to update subscription: {str(e)}")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler"""
    try:
        logger.info("User management API invoked")
        logger.debug(f"Event: {json.dumps(event, default=str)}")
        
        # Extract user from authorizer context
        user_info = get_user_from_context(event)
        user_id = user_info["user_id"]
        
        # Get HTTP method and resource path
        http_method = event.get("httpMethod", "")
        resource_path = event.get("resource", "")
        
        logger.info(f"Processing {http_method} {resource_path} for user {user_id}")
        
        # Route to appropriate handler
        if resource_path == "/user/profile":
            if http_method == "GET":
                profile = get_user_profile(user_id)
                return json_response(200, {"profile": profile})
            
            elif http_method == "PUT":
                body = json.loads(event.get("body", "{}"))
                updated_profile = update_user_profile(user_id, body)
                return json_response(200, {"profile": updated_profile})
        
        elif resource_path == "/user/usage":
            if http_method == "GET":
                # Get optional days parameter
                query_params = event.get("queryStringParameters") or {}
                days = int(query_params.get("days", 30))
                
                usage_data = get_user_usage(user_id, days)
                return json_response(200, {"usage": usage_data})
        
        elif resource_path == "/user/subscription":
            if http_method == "GET":
                subscription = get_user_subscription(user_id)
                return json_response(200, {"subscription": subscription})
            
            elif http_method == "PUT":
                body = json.loads(event.get("body", "{}"))
                plan_type = body.get("plan_type")
                
                if not plan_type:
                    return json_response(400, {"error": "Missing plan_type in request body"})
                
                subscription = update_user_subscription(user_id, plan_type)
                return json_response(200, {"subscription": subscription})
        
        # Route not found
        return json_response(404, {"error": "Endpoint not found"})
        
    except UserManagementError as e:
        logger.warning(f"User management error: {str(e)}")
        return json_response(400, {"error": str(e)})
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return json_response(500, {"error": "Internal server error"})


if __name__ == "__main__":
    # Test handler locally
    test_event = {
        "httpMethod": "GET",
        "resource": "/user/profile", 
        "requestContext": {
            "authorizer": {
                "userId": "test-user-id",
                "username": "testuser",
                "email": "test@example.com"
            }
        }
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))