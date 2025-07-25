#!/usr/bin/env python3
"""
DynamoDB의 프롬프트 카드를 직접 수정하는 스크립트
"""

import boto3
import json

def update_prompt_card(project_id, prompt_title, new_prompt):
    """특정 프롬프트 카드 업데이트"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('title-generator-prompt-meta')
    
    try:
        # 기존 프롬프트 찾기
        response = table.query(
            KeyConditionExpression='projectId = :pid',
            FilterExpression='title = :title',
            ExpressionAttributeValues={
                ':pid': project_id,
                ':title': prompt_title
            }
        )
        
        if response['Items']:
            item = response['Items'][0]
            prompt_id = item['promptId']
            
            # 프롬프트 업데이트
            table.update_item(
                Key={
                    'projectId': project_id,
                    'promptId': prompt_id
                },
                UpdateExpression='SET prompt = :prompt, updatedAt = :now',
                ExpressionAttributeValues={
                    ':prompt': new_prompt,
                    ':now': '2025-07-24T16:00:00Z'
                }
            )
            
            print(f"✅ '{prompt_title}' 프롬프트 업데이트 완료")
            return True
        else:
            print(f"❌ '{prompt_title}' 프롬프트를 찾을 수 없습니다")
            return False
            
    except Exception as e:
        print(f"❌ 프롬프트 업데이트 중 오류: {str(e)}")
        return False

def list_current_prompts(project_id):
    """현재 프롬프트 카드들 조회"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('title-generator-prompt-meta')
    
    try:
        response = table.query(
            KeyConditionExpression='projectId = :pid',
            ExpressionAttributeValues={':pid': project_id}
        )
        
        print(f"\n📋 프로젝트 '{project_id}'의 현재 프롬프트 카드들:")
        print("=" * 60)
        
        for i, item in enumerate(response['Items'], 1):
            print(f"{i}. 제목: {item.get('title', 'Unknown')}")
            print(f"   설명: {item.get('description', 'No description')}")
            print(f"   활성: {item.get('isActive', False)}")
            print(f"   프롬프트 (처음 100자): {item.get('prompt', '')[:100]}...")
            print("-" * 60)
        
        return response['Items']
        
    except Exception as e:
        print(f"❌ 프롬프트 조회 중 오류: {str(e)}")
        return []

if __name__ == "__main__":
    # 사용 예시
    project_id = input("프로젝트 ID를 입력하세요 (기본값: test-project): ").strip() or "test-project"
    
    # 현재 프롬프트들 보기
    current_prompts = list_current_prompts(project_id)
    
    if current_prompts:
        print(f"\n🔧 수정할 프롬프트를 선택하세요:")
        prompt_title = input("프롬프트 제목 입력: ").strip()
        
        print(f"\n📝 새로운 프롬프트 내용을 입력하세요:")
        print("(여러 줄 입력 가능, 끝낼 때는 빈 줄에서 Ctrl+D)")
        
        new_prompt_lines = []
        try:
            while True:
                line = input()
                new_prompt_lines.append(line)
        except EOFError:
            pass
        
        new_prompt = '\n'.join(new_prompt_lines)
        
        if new_prompt.strip():
            update_prompt_card(project_id, prompt_title, new_prompt)
        else:
            print("❌ 프롬프트 내용이 비어있습니다")
    else:
        print("📋 프롬프트 카드가 없습니다")