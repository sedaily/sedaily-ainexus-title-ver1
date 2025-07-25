import json
import boto3
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class FlowIntegrationHandler:
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-agent-runtime')
        self.dynamodb = boto3.resource('dynamodb')
        self.prompt_meta_table = self.dynamodb.Table(os.environ.get('PROMPT_META_TABLE'))
        self.flow_id = os.environ.get('BEDROCK_FLOW_ID')
        
    def lambda_handler(self, event, context):
        """Lambda 핸들러 - Flow 통합 실행"""
        try:
            body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
            
            project_id = body.get('projectId')
            user_input = body.get('userInput')
            
            if not project_id or not user_input:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'error': 'projectId와 userInput이 필요합니다'
                    }, ensure_ascii=False)
                }
            
            # Flow 실행 방식 결정 (기존 ThreadPool vs 새로운 Bedrock Flows)
            use_bedrock_flows = body.get('useBedrokFlows', False)
            
            if use_bedrock_flows and self.flow_id:
                result = self.execute_bedrock_flow(project_id, user_input)
            else:
                result = self.execute_thread_pool_agents(project_id, user_input)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps(result, ensure_ascii=False)
            }
            
        except Exception as e:
            logger.error(f"Flow 통합 실행 중 오류: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': f'Flow 실행 중 오류가 발생했습니다: {str(e)}'
                }, ensure_ascii=False)
            }
    
    def execute_bedrock_flow(self, project_id: str, user_input: str) -> Dict[str, Any]:
        """Bedrock Flows를 사용한 실행"""
        try:
            logger.info(f"Bedrock Flow 실행 시작: {self.flow_id}")
            
            # Flow 실행
            response = self.bedrock_runtime.invoke_flow(
                flowIdentifier=self.flow_id,
                flowAliasIdentifier='TSTALIASID',
                inputs=[
                    {
                        'content': {
                            'document': user_input
                        },
                        'nodeName': 'FlowInputNode',
                        'nodeOutputName': 'userInput'
                    }
                ],
                enableTrace=True
            )
            
            # 스트리밍 응답 처리
            result = self._process_flow_response(response['responseStream'])
            
            # 결과 구조화
            structured_result = {
                'method': 'bedrock_flows',
                'projectId': project_id,
                'userInput': user_input,
                'flowId': self.flow_id,
                'results': result,
                'timestamp': context.aws_request_id if 'context' in locals() else None
            }
            
            logger.info("Bedrock Flow 실행 완료")
            return structured_result
            
        except Exception as e:
            logger.error(f"Bedrock Flow 실행 중 오류: {str(e)}")
            raise
    
    def execute_thread_pool_agents(self, project_id: str, user_input: str) -> Dict[str, Any]:
        """기존 ThreadPool 방식 실행 (fallback)"""
        try:
            logger.info("ThreadPool 에이전트 실행 시작")
            
            # 기존 planner Lambda 호출
            lambda_client = boto3.client('lambda')
            planner_function_name = os.environ.get('PLANNER_FUNCTION_NAME')
            
            response = lambda_client.invoke(
                FunctionName=planner_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'body': json.dumps({
                        'projectId': project_id,
                        'userInput': user_input
                    })
                })
            )
            
            payload = json.loads(response['Payload'].read())
            result_body = json.loads(payload.get('body', '{}'))
            
            structured_result = {
                'method': 'thread_pool',
                'projectId': project_id,
                'userInput': user_input,
                'results': result_body,
                'timestamp': context.aws_request_id if 'context' in locals() else None
            }
            
            logger.info("ThreadPool 에이전트 실행 완료")
            return structured_result
            
        except Exception as e:
            logger.error(f"ThreadPool 실행 중 오류: {str(e)}")
            raise
    
    def _process_flow_response(self, response_stream) -> Dict[str, Any]:
        """Flow 응답 스트림 처리"""
        result = {
            'finalOutput': None,
            'agentOutputs': {},
            'traces': [],
            'errors': []
        }
        
        try:
            for event in response_stream:
                if 'flowOutputEvent' in event:
                    output_event = event['flowOutputEvent']
                    node_name = output_event['nodeName']
                    node_type = output_event['nodeType']
                    
                    if node_type == 'Output':
                        result['finalOutput'] = output_event['content']
                    elif node_type == 'Agent':
                        result['agentOutputs'][node_name] = output_event['content']
                
                elif 'flowTraceEvent' in event:
                    trace_event = event['flowTraceEvent']
                    result['traces'].append({
                        'nodeInputs': trace_event.get('nodeInputs', {}),
                        'nodeOutputs': trace_event.get('nodeOutputs', {}),
                        'nodeName': trace_event.get('nodeName'),
                        'nodeType': trace_event.get('nodeType')
                    })
                
                elif 'internalServerException' in event:
                    result['errors'].append(event['internalServerException'])
                    
        except Exception as e:
            logger.error(f"응답 스트림 처리 중 오류: {str(e)}")
            result['errors'].append(str(e))
        
        return result
    
    def get_prompt_cards(self, project_id: str) -> List[Dict[str, Any]]:
        """프로젝트의 프롬프트 카드들 조회"""
        try:
            response = self.prompt_meta_table.query(
                KeyConditionExpression='projectId = :pid',
                FilterExpression='attribute_exists(isActive) AND isActive = :active',
                ExpressionAttributeValues={
                    ':pid': project_id,
                    ':active': True
                }
            )
            
            return response.get('Items', [])
            
        except Exception as e:
            logger.error(f"프롬프트 카드 조회 중 오류: {str(e)}")
            return []
    
    def compare_execution_methods(self, project_id: str, user_input: str) -> Dict[str, Any]:
        """두 실행 방식 비교"""
        comparison_result = {
            'projectId': project_id,
            'userInput': user_input,
            'methods': {}
        }
        
        try:
            # Bedrock Flows 실행
            if self.flow_id:
                import time
                start_time = time.time()
                flows_result = self.execute_bedrock_flow(project_id, user_input)
                flows_execution_time = time.time() - start_time
                
                comparison_result['methods']['bedrock_flows'] = {
                    'result': flows_result,
                    'execution_time': flows_execution_time,
                    'success': True
                }
            
            # ThreadPool 실행
            start_time = time.time()
            threadpool_result = self.execute_thread_pool_agents(project_id, user_input)
            threadpool_execution_time = time.time() - start_time
            
            comparison_result['methods']['thread_pool'] = {
                'result': threadpool_result,
                'execution_time': threadpool_execution_time,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"실행 방식 비교 중 오류: {str(e)}")
            comparison_result['error'] = str(e)
        
        return comparison_result

# Lambda 핸들러 함수
handler_instance = FlowIntegrationHandler()

def lambda_handler(event, context):
    return handler_instance.lambda_handler(event, context)