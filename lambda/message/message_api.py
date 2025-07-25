import json
import boto3
import os
from datetime import datetime, timezone
from typing import Dict, List
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
messages_table = dynamodb.Table(os.environ['MESSAGES_TABLE'])
conversations_table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])

def handler(event, context):
    """
    Handle message-related API requests
    GET /messages - Get messages for a conversation with pagination
    """
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        # Extract user info from Cognito JWT
        try:
            user_sub = event['requestContext']['authorizer']['claims']['sub']
            if not user_sub:
                raise ValueError("User sub not found in claims")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            print(f"Event requestContext: {event.get('requestContext', {})}")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({'error': 'Authentication required'})
            }
        
        if http_method == 'GET' and path == '/messages':
            return get_messages(user_sub, event.get('queryStringParameters') or {})
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,OPTIONS'
                },
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        print(f"Error in message handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_messages(user_sub: str, query_params: Dict) -> Dict:
    """
    Get messages for a conversation with pagination
    Query params: convId (required), limit (default 50), cursor (ISO timestamp)
    """
    
    conv_id = query_params.get('convId')
    if not conv_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': 'convId is required'})
        }
    
    # Verify user owns this conversation
    if not verify_conversation_ownership(conv_id, user_sub):
        return {
            'statusCode': 403,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': 'Access denied'})
        }
    
    limit = min(int(query_params.get('limit', 50)), 100)  # Max 100 messages
    cursor = query_params.get('cursor')
    
    try:
        # Query messages for conversation
        query_kwargs = {
            'KeyConditionExpression': 'PK = :pk',
            'ExpressionAttributeValues': {
                ':pk': f'CONV#{conv_id}'
            },
            'ScanIndexForward': True,  # Oldest first for chronological order
            'Limit': limit + 1  # Get one extra to determine if there are more
        }
        
        if cursor:
            # Add cursor for pagination (going backwards in time)
            query_kwargs['ExclusiveStartKey'] = {
                'PK': f'CONV#{conv_id}',
                'SK': f'TS#{cursor}'
            }
        
        response = messages_table.query(**query_kwargs)
        items = response.get('Items', [])
        
        # Check if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item
        
        # Format messages
        messages = []
        for item in items:
            messages.append({
                'id': item['SK'].replace('TS#', ''),
                'role': item.get('role'),
                'content': item.get('content', ''),
                'tokenCount': int(item.get('tokenCount', 0)),
                'timestamp': item['SK'].replace('TS#', '')
            })
        
        # Prepare next cursor (for pagination going forward)
        next_cursor = None
        if has_more and messages:
            next_cursor = messages[-1]['timestamp']
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({
                'messages': messages,
                'nextCursor': next_cursor,
                'hasMore': has_more
            }, default=str)
        }
    
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps({'error': 'Failed to retrieve messages'})
        }

def verify_conversation_ownership(conv_id: str, user_sub: str) -> bool:
    """
    Verify that the user owns the conversation
    """
    try:
        response = conversations_table.get_item(
            Key={
                'PK': f'USER#{user_sub}',
                'SK': f'CONV#{conv_id}'
            }
        )
        return 'Item' in response
    except Exception as e:
        print(f"Error verifying conversation ownership: {str(e)}")
        return False

def save_messages(conv_id: str, user_sub: str, messages: List[Dict]) -> bool:
    """
    Save messages to DynamoDB (batch write)
    This function will be called from WebSocket handler
    """
    try:
        # Verify conversation exists and user owns it
        if not verify_conversation_ownership(conv_id, user_sub):
            print(f"User {user_sub} does not own conversation {conv_id}")
            return False
        
        # Prepare messages for batch write
        with messages_table.batch_writer() as batch:
            for message in messages:
                # Calculate TTL (180 days from now)
                ttl = int((datetime.now(timezone.utc).timestamp()) + (180 * 24 * 60 * 60))
                
                # Create message item
                timestamp = message.get('timestamp', datetime.now(timezone.utc).isoformat())
                
                message_item = {
                    'PK': f'CONV#{conv_id}',
                    'SK': f'TS#{timestamp}',
                    'role': message.get('role'),  # 'user' or 'assistant'
                    'content': message.get('content', ''),
                    'tokenCount': message.get('tokenCount', 0),
                    'ttl': ttl
                }
                
                batch.put_item(Item=message_item)
        
        return True
        
    except Exception as e:
        print(f"Error saving messages: {str(e)}")
        return False