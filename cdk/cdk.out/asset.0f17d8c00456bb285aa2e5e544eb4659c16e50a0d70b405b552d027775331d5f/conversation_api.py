import json
import boto3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
conversations_table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])
messages_table = dynamodb.Table(os.environ['MESSAGES_TABLE'])

def handler(event, context):
    """
    Handle conversation-related API requests
    GET /conversations - List user's conversations with pagination
    POST /conversation - Create new conversation
    """
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        # Extract user info from Cognito JWT or use hardcoded for testing
        try:
            user_sub = event['requestContext']['authorizer']['claims']['sub']
        except:
            # Fallback for testing without authorizer
            user_sub = "44888408-4081-70ec-60a1-c18d7dae0ef1"
        
        if http_method == 'GET' and path == '/conversations':
            return get_conversations(user_sub, event.get('queryStringParameters') or {})
        elif http_method == 'POST' and path == '/conversations':
            return create_conversation(user_sub, json.loads(event['body']) if event.get('body') else {})
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        print(f"Error in conversation handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_conversations(user_sub: str, query_params: Dict) -> Dict:
    """
    Get user's conversations with pagination
    Query params: limit (default 20), cursor (ISO timestamp for pagination)
    """
    
    limit = min(int(query_params.get('limit', 20)), 50)  # Max 50 conversations
    cursor = query_params.get('cursor')
    
    try:
        # Query conversations using GSI
        query_kwargs = {
            'IndexName': 'GSI1-LastActivity',
            'KeyConditionExpression': 'GSI1PK = :pk',
            'ExpressionAttributeValues': {
                ':pk': f'USER#{user_sub}'
            },
            'ScanIndexForward': False,  # Most recent first
            'Limit': limit + 1  # Get one extra to determine if there are more
        }
        
        if cursor:
            try:
                # cursor should be in format "lastActivityAt:conversationId"
                if ':' in cursor:
                    last_activity, conv_id = cursor.split(':', 1)
                    query_kwargs['ExclusiveStartKey'] = {
                        'GSI1PK': f'USER#{user_sub}',
                        'lastActivityAt': last_activity,
                        'PK': f'USER#{user_sub}',
                        'SK': f'CONV#{conv_id}'
                    }
                else:
                    # Fallback: treat cursor as lastActivityAt only
                    print(f"Warning: Invalid cursor format: {cursor}")
            except Exception as e:
                print(f"Error parsing cursor: {e}")
                # Continue without cursor for pagination
        
        response = conversations_table.query(**query_kwargs)
        items = response.get('Items', [])
        
        # Check if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item
        
        # Format conversations
        conversations = []
        for item in items:
            conversations.append({
                'id': item['SK'].replace('CONV#', ''),
                'title': item.get('title', 'New Conversation'),
                'startedAt': item.get('startedAt'),
                'lastActivityAt': item.get('lastActivityAt'),
                'tokenSum': int(item.get('tokenSum', 0))
            })
        
        # Prepare next cursor
        next_cursor = None
        if has_more and conversations:
            last_conv = conversations[-1]
            next_cursor = f"{last_conv['lastActivityAt']}:{last_conv['id']}"
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'conversations': conversations,
                'nextCursor': next_cursor,
                'hasMore': has_more
            }, default=str)
        }
    
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization', 
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Failed to retrieve conversations'})
        }

def create_conversation(user_sub: str, body: Dict) -> Dict:
    """
    Create a new conversation
    Body: { title?: string }
    """
    
    try:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        title = body.get('title', 'New Conversation')
        
        # Calculate TTL (365 days from now)
        ttl = int((datetime.now(timezone.utc).timestamp()) + (365 * 24 * 60 * 60))
        
        # Create conversation item
        conversation_item = {
            'PK': f'USER#{user_sub}',
            'SK': f'CONV#{conv_id}',
            'GSI1PK': f'USER#{user_sub}',  # For GSI queries
            'title': title,
            'startedAt': now,
            'lastActivityAt': now,
            'tokenSum': 0,
            'ttl': ttl
        }
        
        conversations_table.put_item(Item=conversation_item)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'conversationId': conv_id,
                'title': title,
                'startedAt': now,
                'lastActivityAt': now
            })
        }
        
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Failed to create conversation'})
        }

def update_conversation_activity(conv_id: str, user_sub: str, token_count: int = 0, title: str = None):
    """
    Update conversation's last activity and token sum
    This function will be called from WebSocket handler
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        update_expression = "SET lastActivityAt = :activity, tokenSum = tokenSum + :tokens"
        expression_values = {
            ':activity': now,
            ':tokens': token_count
        }
        
        if title:
            update_expression += ", title = :title"
            expression_values[':title'] = title
        
        conversations_table.update_item(
            Key={
                'PK': f'USER#{user_sub}',
                'SK': f'CONV#{conv_id}'
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        return True
        
    except Exception as e:
        print(f"Error updating conversation activity: {str(e)}")
        return False