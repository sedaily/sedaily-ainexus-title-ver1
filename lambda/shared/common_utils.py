import json
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger()

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            else:
                return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token"
    }

def create_success_response(data, status_code=200):
    return {
        "statusCode": status_code,
        "headers": get_cors_headers(),
        "body": json.dumps(data, ensure_ascii=False, cls=DecimalEncoder)
    }

def create_error_response(status_code, message, details=None):
    error_data = {
        "error": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    if details:
        error_data["details"] = details
    
    return {
        "statusCode": status_code,
        "headers": get_cors_headers(),
        "body": json.dumps(error_data, ensure_ascii=False)
    }
