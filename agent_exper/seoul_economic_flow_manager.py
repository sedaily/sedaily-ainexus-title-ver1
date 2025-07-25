import boto3
import json
import os
import time
from typing import Dict, Any, Optional

class SeoulEconomicFlowManager:
    def __init__(self, region='us-east-1'):
        self.bedrock_client = boto3.client('bedrock-agent', region_name=region)
        self.flow_arn = None
        self.flow_version = None
        
    def create_flow_from_template(self, template_path: str, flow_name: str) -> str:
        """템플릿에서 Flow 생성"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                flow_template = json.load(f)
            
            # 기존 Flow 확인
            existing_flow = self._get_flow_by_name(flow_name)
            if existing_flow:
                print(f"기존 Flow 발견: {existing_flow['id']}")
                return existing_flow['id']
            
            # 새 Flow 생성
            response = self.bedrock_client.create_flow(
                name=flow_name,
                description=flow_template.get('description', ''),
                definition=flow_template['definition'],
                executionRoleArn=self._get_execution_role_arn(),
                tags=flow_template.get('tags', {})
            )
            
            self.flow_arn = response['arn']
            flow_id = response['id']
            print(f"Flow 생성 완료: {flow_id}")
            
            return flow_id
            
        except Exception as e:
            print(f"Flow 생성 중 오류: {str(e)}")
            raise
    
    def prepare_flow_version(self, flow_id: str) -> str:
        """Flow 버전 준비"""
        try:
            response = self.bedrock_client.prepare_flow(flowIdentifier=flow_id)
            
            # 준비 완료까지 대기
            self._wait_for_flow_status(flow_id, 'Prepared')
            
            self.flow_version = response['version']
            print(f"Flow 버전 준비 완료: {self.flow_version}")
            
            return self.flow_version
            
        except Exception as e:
            print(f"Flow 버전 준비 중 오류: {str(e)}")
            raise
    
    def invoke_flow(self, flow_id: str, user_input: str, enable_trace: bool = True) -> Dict[str, Any]:
        """Flow 실행"""
        try:
            bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
            
            response = bedrock_runtime.invoke_flow(
                flowIdentifier=flow_id,
                flowAliasIdentifier='TSTALIASID',  # 테스트 별칭
                inputs=[
                    {
                        'content': {
                            'document': user_input
                        },
                        'nodeName': 'FlowInputNode',
                        'nodeOutputName': 'userInput'
                    }
                ],
                enableTrace=enable_trace
            )
            
            # 스트리밍 응답 처리
            result = self._process_streaming_response(response['responseStream'])
            
            return result
            
        except Exception as e:
            print(f"Flow 실행 중 오류: {str(e)}")
            raise
    
    def create_agents_for_flow(self, prompt_cards: Dict[str, str]) -> Dict[str, str]:
        """프롬프트 카드를 기반으로 에이전트들 생성"""
        agent_aliases = {}
        
        for agent_name, prompt_template in prompt_cards.items():
            try:
                # 에이전트 생성
                agent_response = self.bedrock_client.create_agent(
                    agentName=f"seoul-economic-{agent_name.lower()}-{int(time.time())}",
                    description=f"서울경제신문 {agent_name} 에이전트",
                    foundationModel="anthropic.claude-3-5-sonnet-20241022-v2:0",
                    instruction=prompt_template,
                    agentResourceRoleArn=self._get_agent_role_arn()
                )
                
                agent_id = agent_response['agent']['agentId']
                
                # 에이전트 준비
                self.bedrock_client.prepare_agent(agentId=agent_id)
                self._wait_for_agent_status(agent_id, 'PREPARED')
                
                # 별칭 생성
                alias_response = self.bedrock_client.create_agent_alias(
                    agentId=agent_id,
                    agentAliasName=f"{agent_name.lower()}-alias"
                )
                
                agent_aliases[f"{agent_name.upper()}_AGENT_ALIAS_ARN"] = alias_response['agentAlias']['agentAliasArn']
                print(f"{agent_name} 에이전트 생성 완료: {agent_id}")
                
            except Exception as e:
                print(f"{agent_name} 에이전트 생성 중 오류: {str(e)}")
                continue
        
        return agent_aliases
    
    def update_flow_with_agents(self, flow_id: str, agent_aliases: Dict[str, str]) -> bool:
        """생성된 에이전트들로 Flow 업데이트"""
        try:
            # 현재 Flow 정의 가져오기
            flow_response = self.bedrock_client.get_flow(flowIdentifier=flow_id)
            flow_definition = flow_response['definition']
            
            # 에이전트 ARN 치환
            flow_definition_str = json.dumps(flow_definition)
            for placeholder, arn in agent_aliases.items():
                flow_definition_str = flow_definition_str.replace(f"$${placeholder}", arn)
            
            updated_definition = json.loads(flow_definition_str)
            
            # Flow 업데이트
            self.bedrock_client.update_flow(
                flowIdentifier=flow_id,
                name=flow_response['name'],
                description=flow_response['description'],
                definition=updated_definition
            )
            
            print("Flow 에이전트 업데이트 완료")
            return True
            
        except Exception as e:
            print(f"Flow 업데이트 중 오류: {str(e)}")
            return False
    
    def _get_flow_by_name(self, flow_name: str) -> Optional[Dict[str, Any]]:
        """이름으로 기존 Flow 검색"""
        try:
            response = self.bedrock_client.list_flows()
            for flow in response.get('flowSummaries', []):
                if flow['name'] == flow_name:
                    return flow
            return None
        except:
            return None
    
    def _wait_for_flow_status(self, flow_id: str, target_status: str, timeout: int = 300):
        """Flow 상태 대기"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.bedrock_client.get_flow(flowIdentifier=flow_id)
                if response['status'] == target_status:
                    return
                time.sleep(10)
            except:
                time.sleep(10)
        raise TimeoutError(f"Flow 상태 {target_status} 대기 시간 초과")
    
    def _wait_for_agent_status(self, agent_id: str, target_status: str, timeout: int = 300):
        """에이전트 상태 대기"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.bedrock_client.get_agent(agentId=agent_id)
                if response['agent']['agentStatus'] == target_status:
                    return
                time.sleep(10)
            except:
                time.sleep(10)
        raise TimeoutError(f"에이전트 상태 {target_status} 대기 시간 초과")
    
    def _process_streaming_response(self, response_stream) -> Dict[str, Any]:
        """스트리밍 응답 처리"""
        result = {
            'outputs': {},
            'traces': [],
            'errors': []
        }
        
        for event in response_stream:
            if 'flowOutputEvent' in event:
                output_event = event['flowOutputEvent']
                node_name = output_event['nodeName']
                node_type = output_event['nodeType']
                
                if node_type == 'Output':
                    result['outputs'][node_name] = output_event['content']
            
            elif 'flowTraceEvent' in event:
                result['traces'].append(event['flowTraceEvent'])
            
            elif 'internalServerException' in event:
                result['errors'].append(event['internalServerException'])
        
        return result
    
    def _get_execution_role_arn(self) -> str:
        """Flow 실행 역할 ARN 반환"""
        account_id = boto3.client('sts').get_caller_identity()['Account']
        return f"arn:aws:iam::{account_id}:role/amazon-bedrock-execution-role-for-flows"
    
    def _get_agent_role_arn(self) -> str:
        """에이전트 역할 ARN 반환"""
        account_id = boto3.client('sts').get_caller_identity()['Account']
        return f"arn:aws:iam::{account_id}:role/AmazonBedrockExecutionRoleForAgents_bedrock-agent-role"

# 테스트 함수
def test_seoul_economic_flow():
    """서울경제 Flow 테스트"""
    flow_manager = SeoulEconomicFlowManager()
    
    # 프롬프트 카드 정의 (기존 DynamoDB에서 가져올 수 있음)
    prompt_cards = {
        "planner": "서울경제신문의 편집 기획자로서 제목을 기획하고 구성해주세요.",
        "journalist": "경험 많은 경제 전문 기자로서 정확하고 매력적인 제목을 작성해주세요.",
        "seo_expert": "SEO 전문가로서 검색 최적화된 제목을 제안해주세요.",
        "social_strategist": "소셜 미디어 전략가로서 공유하고 싶은 제목을 만들어주세요.",
        "data_analyst": "데이터 분석가로서 클릭률이 높은 제목을 제안해주세요."
    }
    
    try:
        # 1. Flow 생성
        template_path = "/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/seoul_economic_multi_agent_flow.json"
        flow_id = flow_manager.create_flow_from_template(template_path, "seoul-economic-title-generator-flow")
        
        # 2. 에이전트들 생성
        agent_aliases = flow_manager.create_agents_for_flow(prompt_cards)
        
        # 3. Flow에 에이전트 연결
        flow_manager.update_flow_with_agents(flow_id, agent_aliases)
        
        # 4. Flow 버전 준비
        version = flow_manager.prepare_flow_version(flow_id)
        
        # 5. 테스트 실행
        test_input = "삼성전자가 신형 스마트폰을 출시한다는 뉴스에 대한 기사 제목을 만들어주세요."
        result = flow_manager.invoke_flow(flow_id, test_input)
        
        print("=== Flow 실행 결과 ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return flow_id, result
        
    except Exception as e:
        print(f"테스트 중 오류: {str(e)}")
        return None, None

if __name__ == "__main__":
    test_seoul_economic_flow()