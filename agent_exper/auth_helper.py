#!/usr/bin/env python3
"""
API 인증 헬퍼
"""

import requests
import json

def create_test_user_and_get_token():
    """테스트 사용자 생성 및 토큰 획득"""
    api_url = "https://nq5qrt16lb.execute-api.us-east-1.amazonaws.com/prod"
    
    # 테스트 사용자 정보
    test_user = {
        "username": "testuser",
        "email": "test@example.com", 
        "password": "TestPassword123!",
        "name": "Test User"
    }
    
    print("👤 테스트 사용자 생성 중...")
    
    try:
        # 1. 사용자 등록
        register_response = requests.post(
            f"{api_url}/auth/register",
            json=test_user,
            headers={'Content-Type': 'application/json'}
        )
        
        if register_response.status_code == 201:
            print("✅ 사용자 등록 성공")
        elif register_response.status_code == 409:
            print("ℹ️  사용자가 이미 존재함")
        else:
            print(f"⚠️ 사용자 등록 응답: {register_response.status_code} - {register_response.text}")
        
        # 2. 로그인하여 토큰 획득
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        login_response = requests.post(
            f"{api_url}/auth/login",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            token = login_result.get('token')
            if token:
                print("✅ 로그인 성공, 토큰 획득")
                return token
            else:
                print("❌ 토큰을 찾을 수 없음")
                return None
        else:
            print(f"❌ 로그인 실패: {login_response.status_code} - {login_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 인증 과정 중 오류: {str(e)}")
        return None

def create_test_project(token):
    """테스트 프로젝트 생성"""
    api_url = "https://nq5qrt16lb.execute-api.us-east-1.amazonaws.com/prod"
    
    project_data = {
        "name": "Seoul Economic Test Project",
        "description": "서울경제신문 멀티-에이전트 테스트 프로젝트"
    }
    
    try:
        response = requests.post(
            f"{api_url}/projects",
            json=project_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
        )
        
        if response.status_code == 201:
            project = response.json()
            project_id = project.get('projectId')
            print(f"✅ 테스트 프로젝트 생성 성공: {project_id}")
            return project_id
        else:
            print(f"❌ 프로젝트 생성 실패: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 프로젝트 생성 중 오류: {str(e)}")
        return None

def save_test_prompts(token, project_id):
    """테스트 프롬프트 카드들 저장"""
    api_url = "https://nq5qrt16lb.execute-api.us-east-1.amazonaws.com/prod"
    
    prompt_cards = [
        {
            "title": "기획자",
            "description": "편집 기획자",
            "prompt": """당신은 서울경제신문의 수석 편집 기획자입니다. 경제 뉴스의 핵심 포인트를 파악하여 독자의 관심을 끌 수 있는 전략적 제목을 기획합니다. 다음 내용에 대해 3개의 제목을 제안해주세요.""",
            "isActive": True
        },
        {
            "title": "기자",
            "description": "경제 전문 기자", 
            "prompt": """당신은 30년 경력의 서울경제신문 경제부 수석기자입니다. 정확한 사실 기반으로 독자가 이해하기 쉬운 명확한 제목을 작성합니다. 다음 내용에 대해 3개의 제목을 작성해주세요.""",
            "isActive": True
        },
        {
            "title": "SEO전문가",
            "description": "검색 최적화 전문가",
            "prompt": """당신은 디지털 미디어 SEO 전문가입니다. 검색엔진 최적화를 고려하여 주요 키워드를 포함한 클릭률 향상 제목을 만듭니다. 다음 내용에 대해 3개의 제목을 제안해주세요.""",
            "isActive": True
        },
        {
            "title": "소셜전략가",
            "description": "소셜 미디어 전문가",
            "prompt": """당신은 소셜 미디어 마케팅 전문가입니다. 공유하고 싶게 만드는 매력적이고 바이럴 가능성이 높은 제목을 만듭니다. 다음 내용에 대해 3개의 제목을 제안해주세요.""",
            "isActive": True
        },
        {
            "title": "데이터분석가",
            "description": "미디어 데이터 분석가",
            "prompt": """당신은 미디어 데이터 분석 전문가입니다. 과거 고성과 제목의 패턴을 활용하여 클릭률이 높을 것으로 예상되는 제목을 만듭니다. 다음 내용에 대해 3개의 제목을 제안해주세요.""",
            "isActive": True
        }
    ]
    
    saved_count = 0
    
    for prompt_card in prompt_cards:
        try:
            response = requests.post(
                f"{api_url}/prompts",
                json={
                    "projectId": project_id,
                    **prompt_card
                },
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                }
            )
            
            if response.status_code in [200, 201]:
                saved_count += 1
                print(f"✅ 프롬프트 카드 저장 성공: {prompt_card['title']}")
            else:
                print(f"⚠️ 프롬프트 카드 저장 실패: {prompt_card['title']} - {response.text}")
                
        except Exception as e:
            print(f"❌ 프롬프트 카드 저장 중 오류: {str(e)}")
    
    print(f"📊 총 {saved_count}/{len(prompt_cards)}개 프롬프트 카드 저장 완료")
    return saved_count > 0

if __name__ == "__main__":
    print("🔐 API 인증 설정 시작")
    print("=" * 40)
    
    # 1. 토큰 획득
    token = create_test_user_and_get_token()
    if not token:
        print("❌ 토큰 획득 실패")
        exit(1)
    
    # 2. 프로젝트 생성
    project_id = create_test_project(token)
    if not project_id:
        print("❌ 프로젝트 생성 실패")
        exit(1)
    
    # 3. 프롬프트 카드 저장
    if save_test_prompts(token, project_id):
        print("\n✅ 인증 설정 완료")
        print(f"🆔 Project ID: {project_id}")
        print(f"🔑 Token: {token[:50]}...")
        
        # 설정 정보 저장
        config = {
            "token": token,
            "project_id": project_id,
            "api_url": "https://nq5qrt16lb.execute-api.us-east-1.amazonaws.com/prod"
        }
        
        with open('/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/test_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("📁 설정이 test_config.json에 저장되었습니다.")
    else:
        print("❌ 프롬프트 카드 저장 실패")