#!/usr/bin/env python3
"""
ThreadPoolExecutor 방식 테스트
"""

import requests
import json
import time

def test_threadpool_method():
    """ThreadPoolExecutor 방식 테스트"""
    print("🧵 ThreadPoolExecutor 방식 테스트 시작")
    print("=" * 50)
    
    # API 엔드포인트
    api_url = "https://nq5qrt16lb.execute-api.us-east-1.amazonaws.com/prod"
    crew_endpoint = f"{api_url}/crew/execute"
    
    # 테스트 케이스
    test_cases = [
        {
            "name": "삼성전자 스마트폰 출시",
            "input": "삼성전자가 신형 갤럭시 스마트폰을 내년 1월 출시한다고 발표했습니다.",
            "projectId": "test-project-001"
        },
        {
            "name": "한국은행 기준금리 인하", 
            "input": "한국은행이 기준금리를 0.25%포인트 인하하여 3.0%로 조정했습니다.",
            "projectId": "test-project-001"
        },
        {
            "name": "네이버 AI 검색 개선",
            "input": "네이버가 AI 검색 서비스를 대폭 개선하여 구글과의 경쟁을 본격화한다고 밝혔습니다.",
            "projectId": "test-project-001"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 테스트 케이스 {i}: {test_case['name']} ---")
        print(f"입력: {test_case['input']}")
        
        payload = {
            "projectId": test_case["projectId"],
            "userInput": test_case["input"]
        }
        
        try:
            # 실행 시간 측정
            start_time = time.time()
            
            response = requests.post(
                crew_endpoint,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=120
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 성공 (실행시간: {execution_time:.2f}초)")
                
                # 결과 출력
                if 'results' in result:
                    agent_results = result['results']
                    print("📊 에이전트별 결과:")
                    
                    for agent_name, agent_result in agent_results.items():
                        if agent_name != 'combined_result':
                            print(f"  🤖 {agent_name}:")
                            if isinstance(agent_result, dict) and 'titles' in agent_result:
                                for title in agent_result['titles'][:2]:  # 처음 2개만 표시
                                    print(f"    - {title}")
                            else:
                                print(f"    - {str(agent_result)[:100]}...")
                    
                    # 최종 결과
                    if 'combined_result' in agent_results:
                        print(f"🎯 최종 결과:")
                        combined = agent_results['combined_result']
                        if isinstance(combined, dict) and 'final_titles' in combined:
                            for title in combined['final_titles'][:3]:
                                print(f"  ⭐ {title}")
                
                results.append({
                    "test_case": test_case['name'],
                    "success": True,
                    "execution_time": execution_time,
                    "result": result
                })
                
            else:
                print(f"❌ 실패 (HTTP {response.status_code})")
                print(f"응답: {response.text}")
                results.append({
                    "test_case": test_case['name'],
                    "success": False,
                    "execution_time": execution_time,
                    "error": response.text
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
    print("📈 ThreadPoolExecutor 방식 테스트 결과 요약")
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
    
    # 실패한 테스트 상세
    if failed_tests:
        print("\n❌ 실패한 테스트:")
        for failed in failed_tests:
            print(f"  - {failed['test_case']}: {failed.get('error', 'Unknown error')}")
    
    return results

if __name__ == "__main__":
    results = test_threadpool_method()
    
    # 결과를 JSON 파일로 저장
    with open('/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/threadpool_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\n📁 결과가 threadpool_test_results.json에 저장되었습니다.")