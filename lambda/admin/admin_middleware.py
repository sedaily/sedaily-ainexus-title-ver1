#!/usr/bin/env python3
"""
Admin Middleware for Role-Based Access Control
Provides decorators and utilities for admin-only endpoints
"""

import json
import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger()

class AdminAccessError(Exception):
    """Custom exception for admin access violations"""
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

def extract_user_context(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract user information from API Gateway authorizer context"""
    try:
        context = event.get("requestContext", {}).get("authorizer", {})
        
        user_id = context.get("userId")
        username = context.get("username", "")
        email = context.get("email", "")
        groups = context.get("groups", "")  # Comma-separated string
        
        if not user_id:
            raise AdminAccessError("Missing user ID in authorization context")
        
        # Convert groups string to list
        user_groups = [g.strip() for g in groups.split(",") if g.strip()] if groups else []
        
        return {
            "user_id": user_id,
            "username": username,
            "email": email,
            "groups": user_groups
        }
    except Exception as e:
        logger.error(f"Failed to extract user context: {str(e)}")
        raise AdminAccessError("Invalid authorization context")

def is_admin_user(user_groups: list) -> bool:
    """Check if user has admin privileges"""
    return "admin" in user_groups

def require_admin(handler_func: Callable) -> Callable:
    """Decorator that requires admin privileges for endpoint access"""
    @wraps(handler_func)
    def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        try:
            # Extract user context
            user_context = extract_user_context(event)
            user_groups = user_context.get("groups", [])
            
            # Check admin privileges
            if not is_admin_user(user_groups):
                logger.warning(f"Non-admin user {user_context['user_id']} attempted to access admin endpoint")
                return json_response(403, {
                    "error": "관리자 권한이 필요합니다",
                    "message": "Admin privileges required"
                })
            
            logger.info(f"Admin user {user_context['user_id']} accessing endpoint")
            
            # Add user context to event for handler use
            event["admin_context"] = user_context
            
            # Call the actual handler
            return handler_func(event, context)
            
        except AdminAccessError as e:
            logger.warning(f"Admin access error: {str(e)}")
            return json_response(401, {
                "error": "인증 오류",
                "message": str(e)
            })
        except Exception as e:
            logger.error(f"Admin middleware error: {str(e)}", exc_info=True)
            return json_response(500, {
                "error": "서버 내부 오류",
                "message": "Internal server error"
            })
    
    return wrapper

def get_admin_context(event: Dict[str, Any]) -> Dict[str, str]:
    """Get admin context from event (should be called from within @require_admin decorated function)"""
    admin_context = event.get("admin_context")
    if not admin_context:
        raise AdminAccessError("Admin context not found - ensure @require_admin decorator is used")
    return admin_context