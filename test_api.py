#!/usr/bin/env python3
"""
TITLE-NOMICS API 테스트 스크립트
CORS 오류 해결 후 API 엔드포인트 테스트
"""

import requests
import json
import sys

# API 기본 URL
API_BASE_URL = "https://vph0fu827a.execute-api.us-east-1.amazonaws.com/prod"

def test_cors_preflight():
    """CORS preflight 요청 테스트"""
    print("=== CORS Preflight 테스트 ===")
    
    endpoints = [
        "/projects",
        "/categories", 
        "/auth/signup"
    ]
    
    for endpoint in endpoints:
        url = f"{API_BASE_URL}{endpoint}"
        print(f"\n테스트 중: OPTIONS {endpoint}")
        
        try:
            response = requests.options(url, headers={
                'Origin': 'http://localhost:3000',
                'Access-Control-Request-Method': 'GET',
                'Access-Control-Request-Headers': 'Content-Type'
            })
            
            print(f"Status: {response.status_code}")
            print(f"CORS Headers:")
            for header, value in response.headers.items():
                if 'access-control' in header.lower():
                    print(f"  {header}: {value}")
                    
        except Exception as e:
            print(f"오류: {str(e)}")

def test_api_endpoints():
    """실제 API 엔드포인트 테스트 (인증 없이)"""
    print("\n=== API 엔드포인트 테스트 ===")
    
    # 1. 카테고리 조회 (인증 불필요한 엔드포인트가 있다면)
    print(f"\n테스트 중: GET /categories")
    try:
        url = f"{API_BASE_URL}/categories"
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
    except Exception as e:
        print(f"오류: {str(e)}")

def test_signup():
    """회원가입 테스트"""
    print(f"\n테스트 중: POST /auth/signup")
    
    test_data = {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "fullname": "테스트 사용자"
    }
    
    try:
        url = f"{API_BASE_URL}/auth/signup"
        response = requests.post(url, 
                               json=test_data,
                               headers={'Content-Type': 'application/json'})
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"오류: {str(e)}")

if __name__ == "__main__":
    print("TITLE-NOMICS API 테스트 시작\n")
    
    # CORS preflight 테스트
    test_cors_preflight()
    
    # API 엔드포인트 테스트
    test_api_endpoints()
    
    # 회원가입 테스트 (옵션)
    if len(sys.argv) > 1 and sys.argv[1] == "--signup":
        test_signup()
    
    print("\n테스트 완료!")