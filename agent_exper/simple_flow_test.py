#!/usr/bin/env python3
"""
기존 Agent를 사용한 간단한 Flow 테스트
"""

import boto3
import json
import time

def test_simple_bedrock_flow():
    """기존 Agent를 사용한 간단한 Flow 테스트"""
    print("🌊 Bedrock Flows 간단 테스트")
    print("=" * 40)
    
    bedrock_client = boto3.client('bedrock-agent')
    
    # 기존 Agent ARN 구성
    account_id = "887078546492"
    region = "us-east-1" 
    agent_id = "RQPEUKAMVX"
    agent_alias_id = "TSTALIASID"
    
    agent_alias_arn = f"arn:aws:bedrock:{region}:{account_id}:agent-alias/{agent_id}/{agent_alias_id}"
    print(f"🤖 사용할 Agent ARN: {agent_alias_arn}")
    
    # 간단한 Flow 정의 (1개 Agent만 사용)
    simple_flow_definition = {
        "connections": [
            {
                "configuration": {
                    "data": {
                        "sourceOutput": "document",
                        "targetInput": "agentInputText"
                    }
                },
                "name": "InputToAgent",
                "source": "FlowInputNode",
                "target": "TestAgent",
                "type": "Data"
            },
            {
                "configuration": {
                    "data": {
                        "sourceOutput": "agentResponse",
                        "targetInput": "document"
                    }
                },
                "name": "AgentToOutput",
                "source": "TestAgent",
                "target": "FlowOutputNode",
                "type": "Data"
            }
        ],
        "nodes": [
            {
                "configuration": {
                    "input": {}
                },
                "name": "FlowInputNode",
                "outputs": [
                    {
                        "name": "document",
                        "type": "String"
                    }
                ],
                "type": "Input"
            },
            {
                "configuration": {
                    "agent": {
                        "agentAliasArn": agent_alias_arn
                    }
                },
                "inputs": [
                    {
                        "expression": "$.data",
                        "name": "agentInputText",
                        "type": "String"
                    }
                ],
                "name": "TestAgent",
                "outputs": [
                    {
                        "name": "agentResponse",
                        "type": "String"
                    }
                ],
                "type": "Agent"
            },
            {
                "configuration": {
                    "output": {}
                },
                "inputs": [
                    {
                        "expression": "$.data",
                        "name": "document",
                        "type": "String"
                    }
                ],
                "name": "FlowOutputNode",
                "type": "Output"
            }
        ]
    }
    
    try:
        # Flow 생성
        print("🏗️  Flow 생성 중...")
        flow_name = f"simple-test-flow-{int(time.time())}"
        
        create_response = bedrock_client.create_flow(
            name=flow_name,
            description="간단한 테스트 Flow",
            definition=simple_flow_definition,
            executionRoleArn=f"arn:aws:iam::{account_id}:role/amazon-bedrock-execution-role-for-flows",
            tags={"Environment": "test"}
        )
        
        flow_id = create_response['id']
        flow_arn = create_response['arn']
        print(f"✅ Flow 생성 성공: {flow_id}")
        
        # Flow 준비
        print("📦 Flow 준비 중...")
        prepare_response = bedrock_client.prepare_flow(flowIdentifier=flow_id)
        
        # 준비 완료 대기
        print("⏳ Flow 준비 완료 대기 중...")
        max_wait = 300  # 5분
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait:
            status_response = bedrock_client.get_flow(flowIdentifier=flow_id)
            status = status_response['status']
            
            print(f"   현재 상태: {status}")
            
            if status == 'Prepared':
                print("✅ Flow 준비 완료!")
                break
            elif status == 'Failed':
                print("❌ Flow 준비 실패")
                return False
            
            time.sleep(10)
        
        if time.time() - start_wait >= max_wait:
            print("⏰ Flow 준비 시간 초과")
            return False
        
        # Flow 테스트 실행
        print("\n🧪 Flow 테스트 실행")
        bedrock_runtime = boto3.client('bedrock-agent-runtime')
        
        test_inputs = [
            "삼성전자가 신형 스마트폰을 출시한다는 뉴스에 대한 기사 제목을 3개 만들어주세요.",
            "한국은행 기준금리 인하 소식에 대한 매력적인 제목을 제안해주세요.",
        ]
        
        for i, test_input in enumerate(test_inputs, 1):
            print(f"\n--- 테스트 {i} ---")
            print(f"입력: {test_input}")
            
            try:
                start_time = time.time()
                
                response = bedrock_runtime.invoke_flow(
                    flowIdentifier=flow_id,
                    flowAliasIdentifier='TSTALIASID',
                    inputs=[
                        {
                            'content': {
                                'document': test_input
                            },
                            'nodeName': 'FlowInputNode',
                            'nodeOutputName': 'document'
                        }
                    ],
                    enableTrace=True
                )
                
                execution_time = time.time() - start_time
                
                # 스트리밍 응답 처리
                print("📤 응답 수신 중...")
                for event in response['responseStream']:
                    if 'flowOutputEvent' in event:
                        output_event = event['flowOutputEvent']
                        if output_event['nodeType'] == 'Output':
                            print(f"✅ 결과 (실행시간: {execution_time:.2f}초):")
                            print(f"   {output_event['content']['document']}")
                            break
                    elif 'flowTraceEvent' in event:
                        trace = event['flowTraceEvent']
                        print(f"   🔍 추적: {trace.get('nodeName', 'Unknown')} - {trace.get('nodeType', 'Unknown')}")
                
            except Exception as e:
                print(f"❌ 테스트 {i} 실행 오류: {str(e)}")
        
        print(f"\n🎯 Flow ID: {flow_id}")
        print("✅ Bedrock Flow 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ Flow 테스트 중 오류: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_simple_bedrock_flow()
    if success:
        print("\n🎉 Bedrock Flow 실험 성공!")
    else:
        print("\n😞 Bedrock Flow 실험 실패")