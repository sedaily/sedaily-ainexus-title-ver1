#!/usr/bin/env python3
import requests
import json

# API 기본 URL
API_URL = "https://gcm3qzoy04.execute-api.us-east-1.amazonaws.com/prod"

def test_categories():
    """카테고리 목록 조회 테스트"""
    print("=== 카테고리 목록 조회 테스트 ===")
    try:
        response = requests.get(f"{API_URL}/categories")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

def test_projects():
    """프로젝트 목록 조회 테스트"""
    print("=== 프로젝트 목록 조회 테스트 ===")
    try:
        response = requests.get(f"{API_URL}/projects")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

def test_create_project():
    """프로젝트 생성 테스트"""
    print("=== 프로젝트 생성 테스트 ===")
    try:
        data = {
            "name": "테스트 프로젝트",
            "description": "API 테스트용 프로젝트",
            "category": "general"
        }
        response = requests.post(f"{API_URL}/projects", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
        
        if response.status_code == 201:
            project_data = response.json()
            return project_data.get('projectId')
    except Exception as e:
        print(f"Error: {e}")
        print()
    return None

def test_create_prompt(project_id):
    """프롬프트 카드 생성 테스트"""
    if not project_id:
        print("프로젝트 ID가 없어 프롬프트 카드 테스트를 건너뜁니다.")
        return
    
    print("=== 프롬프트 카드 생성 테스트 ===")
    try:
        data = {
            "title": "테스트 프롬프트",
            "content": "이것은 테스트용 프롬프트 내용입니다. 최소 10자 이상이어야 합니다.",
            "stepOrder": 1
        }
        response = requests.post(f"{API_URL}/prompts/{project_id}", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

def test_get_prompts(project_id):
    """프롬프트 카드 목록 조회 테스트"""
    if not project_id:
        print("프로젝트 ID가 없어 프롬프트 목록 테스트를 건너뜁니다.")
        return
    
    print("=== 프롬프트 카드 목록 조회 테스트 ===")
    try:
        response = requests.get(f"{API_URL}/prompts/{project_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        print()

if __name__ == "__main__":
    print("🧪 API 테스트 시작\n")
    
    # 1. 카테고리 조회 테스트
    test_categories()
    
    # 2. 프로젝트 목록 조회 테스트
    test_projects()
    
    # 3. 프로젝트 생성 테스트
    project_id = test_create_project()
    
    # 4. 프롬프트 카드 생성 테스트
    test_create_prompt(project_id)
    
    # 5. 프롬프트 카드 목록 조회 테스트
    test_get_prompts(project_id)
    
    print("🏁 API 테스트 완료") 