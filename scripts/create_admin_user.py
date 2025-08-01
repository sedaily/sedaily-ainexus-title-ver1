#!/usr/bin/env python3
"""
관리자 사용자 생성 스크립트
"""
import boto3
import json
import uuid
from datetime import datetime
import sys

def create_admin_user(email, password, env="prod"):
    """
    관리자 사용자를 생성하고 admin 그룹에 추가합니다.
    """
    print(f"\n🔧 관리자 계정 생성을 시작합니다...")
    print(f"   Email: {email}")
    print(f"   Environment: {env}")
    
    # AWS 클라이언트 초기화
    cognito = boto3.client('cognito-idp')
    dynamodb = boto3.resource('dynamodb')
    
    # 환경별 설정
    user_pool_name = f"nexus-title-generator-users-{env}"
    users_table_name = f"nexus-title-generator-users-{env}"
    
    try:
        # 1. User Pool ID 찾기
        print("\n1️⃣ Cognito User Pool 검색 중...")
        pools = cognito.list_user_pools(MaxResults=60)
        user_pool = None
        
        for pool in pools['UserPools']:
            if pool['Name'] == user_pool_name:
                user_pool = pool
                break
        
        if not user_pool:
            print(f"❌ User Pool '{user_pool_name}'을 찾을 수 없습니다.")
            return False
        
        user_pool_id = user_pool['Id']
        print(f"✅ User Pool 찾음: {user_pool_id}")
        
        # 2. 사용자 생성
        print("\n2️⃣ Cognito 사용자 생성 중...")
        try:
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                TemporaryPassword=password,
                MessageAction='SUPPRESS'  # 이메일 전송 억제
            )
            
            user_sub = None
            for attr in response['User']['Attributes']:
                if attr['Name'] == 'sub':
                    user_sub = attr['Value']
                    break
            
            print(f"✅ 사용자 생성됨: {user_sub}")
            
        except cognito.exceptions.UsernameExistsException:
            print("⚠️  사용자가 이미 존재합니다. 기존 사용자 정보를 조회합니다...")
            response = cognito.admin_get_user(
                UserPoolId=user_pool_id,
                Username=email
            )
            
            user_sub = None
            for attr in response['UserAttributes']:
                if attr['Name'] == 'sub':
                    user_sub = attr['Value']
                    break
            
            print(f"✅ 기존 사용자 조회됨: {user_sub}")
        
        # 3. 영구 비밀번호 설정
        print("\n3️⃣ 영구 비밀번호 설정 중...")
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=password,
            Permanent=True
        )
        print("✅ 비밀번호 설정 완료")
        
        # 4. admin 그룹에 추가
        print("\n4️⃣ admin 그룹에 추가 중...")
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=email,
                GroupName='admin'
            )
            print("✅ admin 그룹에 추가됨")
        except cognito.exceptions.ResourceNotFoundException:
            print("⚠️  admin 그룹이 없습니다. 그룹 생성을 시도합니다...")
            # 그룹이 없는 경우는 스택 배포 중 오류가 있었을 수 있음
            pass
        
        # 5. DynamoDB에 사용자 정보 저장
        print("\n5️⃣ DynamoDB에 사용자 정보 저장 중...")
        users_table = dynamodb.Table(users_table_name)
        
        try:
            users_table.put_item(
                Item={
                    'user_id': user_sub,
                    'email': email,
                    'role': 'admin',
                    'created_at': datetime.utcnow().isoformat(),
                    'updated_at': datetime.utcnow().isoformat(),
                    'status': 'active'
                }
            )
            print("✅ DynamoDB에 저장 완료")
        except Exception as e:
            print(f"⚠️  DynamoDB 저장 실패 (테이블이 없을 수 있음): {str(e)}")
        
        print("\n🎉 관리자 계정 생성이 완료되었습니다!")
        print(f"\n로그인 정보:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   User ID: {user_sub}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    # 기본값
    email = "ai@sedaily.com"
    password = "Sedaily2024!"
    env = "prod"
    
    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    if len(sys.argv) > 3:
        env = sys.argv[3]
    
    create_admin_user(email, password, env)