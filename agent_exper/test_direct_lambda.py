#!/usr/bin/env python3
"""
Lambda 직접 호출로 ThreadPool 방식 테스트
"""

import boto3
import json
import time

def test_threadpool_via_lambda():
    """Lambda 직접 호출로 ThreadPool 방식 테스트"""
    print("🧵 Lambda 직접 호출 - ThreadPool 방식 테스트")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "삼성전자 스마트폰 출시",
            "input": "삼성전자가 신형 갤럭시 S25를 내년 1월 출시한다고 발표했습니다. 새로운 AI 기능과 개선된 카메라가 탑재됩니다.",
        },
        {
            "name": "한국은행 기준금리 인하", 
            "input": "한국은행이 기준금리를 0.25%포인트 인하하여 3.0%로 조정했습니다. 경기 부양을 위한 통화정책 완화 조치입니다.",
        },
        {
            "name": "네이버 AI 검색 개선",
            "input": "네이버가 AI 검색 서비스 '하이퍼클로바X'를 대폭 개선하여 구글과의 경쟁을 본격화한다고 밝혔습니다.",
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 테스트 케이스 {i}: {test_case['name']} ---")
        print(f"입력: {test_case['input']}")
        
        # planner Lambda 직접 호출 payload
        payload = {
            "body": json.dumps({
                "projectId": "test-direct-project",
                "userInput": test_case["input"],
                "enableParallel": True
            })
        }
        
        try:
            start_time = time.time()
            
            # PlannerFunction 호출
            response = lambda_client.invoke(
                FunctionName='BedrockDiyTitleGeneratorStack-PlannerFunction5B7E9A8E-5OYE2JxAIXbN',
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            execution_time = time.time() - start_time
            
            # 응답 처리
            response_payload = json.loads(response['Payload'].read())
            
            if response.get('StatusCode') == 200:
                print(f"✅ Lambda 호출 성공 (실행시간: {execution_time:.2f}초)")
                
                # 응답 body 파싱
                if 'body' in response_payload:
                    try:
                        body = json.loads(response_payload['body'])
                        print("📊 결과:")
                        
                        # 각 에이전트 결과 출력
                        for key, value in body.items():
                            if isinstance(value, dict):
                                print(f"  🤖 {key}:")
                                if 'titles' in value:
                                    for title in value['titles'][:2]:
                                        print(f"    - {title}")
                                elif 'final_titles' in value:
                                    for title in value['final_titles'][:2]:
                                        print(f"    ⭐ {title}")
                            elif isinstance(value, list):
                                print(f"  📝 {key}:")
                                for item in value[:2]:
                                    print(f"    - {item}")
                        
                        results.append({
                            "test_case": test_case['name'],
                            "success": True,
                            "execution_time": execution_time,
                            "result": body
                        })
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ 응답 파싱 오류: {e}")
                        print(f"Raw body: {response_payload.get('body', 'No body')}")
                        results.append({
                            "test_case": test_case['name'],
                            "success": False,
                            "execution_time": execution_time,
                            "error": f"Response parsing error: {e}"
                        })
                else:
                    print("⚠️ 응답에 body가 없음")
                    results.append({
                        "test_case": test_case['name'],
                        "success": False,
                        "execution_time": execution_time,
                        "error": "No body in response"
                    })
            else:
                print(f"❌ Lambda 호출 실패 (StatusCode: {response.get('StatusCode')})")
                print(f"응답: {response_payload}")
                results.append({
                    "test_case": test_case['name'],
                    "success": False,
                    "execution_time": execution_time,
                    "error": f"Lambda invocation failed: {response_payload}"
                })
                
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ 오류: {str(e)}")
            results.append({
                "test_case": test_case['name'],
                "success": False,
                "execution_time": execution_time,
                "error": str(e)
            })
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📈 ThreadPool Lambda 직접 호출 테스트 결과")
    print("=" * 50)
    
    successful_tests = [r for r in results if r['success']]
    failed_tests = [r for r in results if not r['success']]
    
    print(f"✅ 성공: {len(successful_tests)}/{len(results)}")
    print(f"❌ 실패: {len(failed_tests)}/{len(results)}")
    
    if successful_tests:
        avg_time = sum(r['execution_time'] for r in successful_tests) / len(successful_tests)
        min_time = min(r['execution_time'] for r in successful_tests)
        max_time = max(r['execution_time'] for r in successful_tests)
        
        print(f"⏱️  평균 실행시간: {avg_time:.2f}초")
        print(f"⚡ 최단 실행시간: {min_time:.2f}초") 
        print(f"🐌 최장 실행시간: {max_time:.2f}초")
    
    return results

if __name__ == "__main__":
    results = test_threadpool_via_lambda()
    
    # 결과 저장
    with open('/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/threadpool_lambda_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n📁 결과가 threadpool_lambda_results.json에 저장되었습니다.")