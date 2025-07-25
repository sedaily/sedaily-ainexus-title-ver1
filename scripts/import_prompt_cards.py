#!/usr/bin/env python3
"""
기존 프롬프트 파일들을 DynamoDB prompt_meta 테이블에 카드로 등록하는 스크립트
"""

import json
import os
import boto3
import uuid
from datetime import datetime
from typing import Dict, List

# AWS 설정
REGION = "us-east-1"  # 필요에 따라 수정
PROMPT_META_TABLE = "title-generator-prompt-meta-v2-auth"
PROJECT_ID = "default-seoul-economic"  # 기본 프로젝트 ID

# DynamoDB 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(PROMPT_META_TABLE)

def read_file_content(file_path: str) -> str:
    """파일 내용을 읽어서 반환"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return ""

def create_prompt_card(
    project_id: str,
    title: str,
    content: str,
    card_type: str,
    step_order: int,
    placeholders: List[str] = None
) -> Dict:
    """프롬프트 카드를 생성하여 DynamoDB에 저장"""
    
    prompt_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'projectId': project_id,
        'promptId': prompt_id,
        'title': title,
        'content': content,
        'type': card_type,
        'stepOrder': step_order,
        'isActive': True,
        'placeholders': placeholders or [],
        'createdAt': timestamp,
        'updatedAt': timestamp,
        'version': 1,
        'metadata': {
            'source': 'import_script',
            'originalFile': f"{card_type}.txt"
        }
    }
    
    try:
        table.put_item(Item=item)
        print(f"✓ Created card: {title} (type: {card_type})")
        return item
    except Exception as e:
        print(f"✗ Error creating card {title}: {str(e)}")
        return None

def extract_placeholders(content: str) -> List[str]:
    """콘텐츠에서 placeholder들을 추출"""
    import re
    placeholders = re.findall(r'\{([^}]+)\}', content)
    return list(set(placeholders))  # 중복 제거

def main():
    """메인 실행 함수"""
    print("=== 서울경제신문 프롬프트 카드 가져오기 ===\n")
    
    # 파일 매핑 정의
    prompt_files = [
        {
            'file': 'main_instruction.txt',
            'title': '메인 지침서',
            'type': 'main_instruction',
            'step_order': 1,
            'description': 'TITLE-NOMICS 프로젝트의 핵심 지침과 워크플로우'
        },
        {
            'file': 'role.txt',
            'title': '프로젝트 역할 정의',
            'type': 'role_definition',
            'step_order': 2,
            'description': '프로젝트 개요와 팀 구조, 목표 정의'
        },
        {
            'file': 'stylebook.txt',
            'title': '서울경제신문 스타일 가이드',
            'type': 'style_guide',
            'step_order': 3,
            'description': '뉴스 작성 기준과 스타일 규칙'
        },
        {
            'file': 'background.txt',
            'title': '배경 컨텍스트',
            'type': 'background_context',
            'step_order': 4,
            'description': '프로젝트 배경 정보와 맥락'
        },
        {
            'file': 'writer_info.txt',
            'title': '작성자 정보',
            'type': 'writer_info',
            'step_order': 5,
            'description': '작성자별 특성과 역할 정보'
        },
        {
            'file': 'guide.txt',
            'title': '운영 가이드',
            'type': 'guide_rules',
            'step_order': 6,
            'description': '실무 운영 규칙과 가이드라인'
        },
        {
            'file': 'article_sample.txt',
            'title': '기사 샘플',
            'type': 'article_sample',
            'step_order': 7,
            'description': '참고용 기사 샘플과 예시'
        }
    ]
    
    created_cards = []
    
    # 각 파일을 읽어서 카드로 생성
    for prompt_file in prompt_files:
        file_path = prompt_file['file']
        
        if not os.path.exists(file_path):
            print(f"⚠ Warning: File {file_path} not found, skipping...")
            continue
        
        print(f"Processing {file_path}...")
        
        # 파일 내용 읽기
        content = read_file_content(file_path)
        
        if not content:
            print(f"⚠ Warning: File {file_path} is empty, skipping...")
            continue
        
        # placeholder 추출
        placeholders = extract_placeholders(content)
        
        # 카드 생성
        card = create_prompt_card(
            project_id=PROJECT_ID,
            title=prompt_file['title'],
            content=content,
            card_type=prompt_file['type'],
            step_order=prompt_file['step_order'],
            placeholders=placeholders
        )
        
        if card:
            created_cards.append(card)
            if placeholders:
                print(f"  → Found placeholders: {', '.join(placeholders)}")
        
        print()
    
    # 결과 요약
    print("=== 가져오기 완료 ===")
    print(f"총 {len(created_cards)}개의 카드가 생성되었습니다.")
    
    if created_cards:
        print("\n생성된 카드 목록:")
        for card in created_cards:
            print(f"- {card['title']} (ID: {card['promptId'][:8]}...)")
            if card['placeholders']:
                print(f"  Placeholders: {', '.join(card['placeholders'])}")
    
    print(f"\nProject ID: {PROJECT_ID}")
    print(f"DynamoDB Table: {PROMPT_META_TABLE}")

def create_sample_instance():
    """샘플 인스턴스 생성 (테스트용)"""
    print("\n=== 샘플 인스턴스 생성 ===")
    
    # prompt_instance 테이블에 샘플 데이터 생성
    instance_table = dynamodb.Table("title-generator-prompt-instances-auth")
    
    instance_id = str(uuid.uuid4())
    
    sample_instance = {
        'projectId': PROJECT_ID,
        'instanceId': instance_id,
        'userId': 'sample-user',
        'createdAt': datetime.utcnow().isoformat(),
        'updatedAt': datetime.utcnow().isoformat(),
        'placeholderValues': {
            'topic': 'AI 기술',
            'timeframe': '2024년',
            'sector': '기술',
            'target_audience': '일반 독자'
        },
        'status': 'active',
        'metadata': {
            'source': 'sample_creation',
            'purpose': 'testing'
        }
    }
    
    try:
        instance_table.put_item(Item=sample_instance)
        print(f"✓ Sample instance created: {instance_id}")
        print(f"  → This will trigger crew_builder_lambda via DynamoDB Streams")
    except Exception as e:
        print(f"✗ Error creating sample instance: {str(e)}")

if __name__ == "__main__":
    main()
    
    # 샘플 인스턴스도 생성할지 묻기
    create_sample = input("\n샘플 인스턴스를 생성하시겠습니까? (y/N): ").lower()
    if create_sample in ['y', 'yes']:
        create_sample_instance()
    
    print("\n완료!") 