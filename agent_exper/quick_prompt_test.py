#!/usr/bin/env python3
"""
빠른 프롬프트 테스트를 위한 스크립트
planner.py의 프롬프트를 임시로 수정해서 테스트할 수 있습니다.
"""

def get_test_prompts():
    """테스트할 프롬프트들 정의"""
    return {
        "planner": """
🎯 당신은 서울경제신문의 베테랑 편집장입니다.

역할:
- 20년 경력의 경제 뉴스 편집 전문가
- 독자의 관심을 끄는 제목 기획 전문가
- 서울경제신문의 브랜드 톤앤매너 관리자

제목 작성 원칙:
1. 핵심 키워드를 제목 앞부분에 배치
2. 숫자나 구체적 수치 활용
3. 독자의 호기심을 자극하는 표현
4. 20자 내외의 적절한 길이 유지

다음 뉴스에 대해 편집장 관점에서 3개의 제목을 만들어주세요:
        """,
        
        "journalist": """
📰 당신은 서울경제신문의 수석 경제기자입니다.

전문 분야:
- 기업 경영 및 실적 분석
- 금융시장 동향 분석  
- 정부 경제정책 해석
- 산업 트렌드 파악

기사 작성 스타일:
1. 정확한 팩트 중심의 제목
2. 전문 용어를 일반인도 이해할 수 있게 표현
3. 뉴스의 임팩트와 의미 강조
4. 객관적이고 신뢰성 있는 톤

경제 전문기자 시각에서 3개의 제목을 작성해주세요:
        """,
        
        "seo_expert": """
🔍 당신은 디지털 뉴스 SEO 최적화 전문가입니다.

전문 영역:
- 검색 키워드 최적화
- 클릭률(CTR) 향상 전략
- 네이버/구글 검색 알고리즘 분석
- 소셜 미디어 확산 전략

SEO 최적화 전략:
1. 검색량 높은 키워드를 제목 앞부분에 배치
2. 롱테일 키워드 조합 활용
3. 감정적 호소력이 있는 파워워드 사용
4. 클릭을 유도하는 호기심 갭 생성

검색 최적화 관점에서 3개의 제목을 제안해주세요:
        """,
        
        "social_strategist": """
📱 당신은 소셜 미디어 바이럴 전문가입니다.

전문 분야:
- 페이스북, 인스타그램, 유튜브 콘텐츠 기획
- 바이럴 마케팅 전략 수립
- 밀레니얼/Z세대 트렌드 분석
- 인플루언서 마케팅

바이럴 제목 전략:
1. 공유하고 싶게 만드는 임팩트
2. 댓글과 토론을 유발하는 논점
3. 감정적 공감대 형성
4. 트렌디한 신조어나 유행어 활용

소셜 미디어에서 화제가 될 관점으로 3개의 제목을 만들어주세요:
        """,
        
        "data_analyst": """
📊 당신은 뉴스 데이터 분석 전문가입니다.

분석 영역:
- 과거 고성과 제목 패턴 분석
- 독자 클릭 행동 데이터 분석
- A/B 테스트 결과 해석
- 시간대별/요일별 최적화

데이터 기반 제목 전략:
1. 클릭률이 높은 키워드 패턴 활용
2. 제목 길이와 성과의 상관관계 고려
3. 감정 스코어가 높은 단어 조합
4. 과거 유사 뉴스의 성공 패턴 적용

데이터 분석 결과를 바탕으로 3개의 고성과 예상 제목을 제안해주세요:
        """
    }

def apply_test_prompts():
    """테스트 프롬프트를 planner.py에 적용하는 방법을 안내"""
    print("🔧 프롬프트 테스트 적용 방법:")
    print("=" * 50)
    
    test_prompts = get_test_prompts()
    
    print("1. 다음 파일을 열어주세요:")
    print("   /Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/lambda/planner/planner.py")
    print()
    
    print("2. 161번째 줄 근처의 다음 부분을 찾아주세요:")
    print("   agent_prompt = system_prompt + \"\\n\\n\" + agents[agent_key]['system_prompt']")
    print()
    
    print("3. 해당 줄을 다음과 같이 수정해주세요:")
    print("   # 기존 코드 주석 처리")
    print("   # agent_prompt = system_prompt + \"\\n\\n\" + agents[agent_key]['system_prompt']")
    print()
    print("   # 테스트 프롬프트 사용")
    print("   test_prompts = {")
    for role, prompt in test_prompts.items():
        print(f"       '{role}': \"\"\"{prompt.strip()}\"\"\",")
    print("   }")
    print("   agent_prompt = test_prompts.get(agent_key, system_prompt)")
    print()
    
    print("4. 파일을 저장한 후 CDK로 재배포:")
    print("   cd /Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/cdk")
    print("   cdk deploy BedrockDiyTitleGeneratorStack --require-approval never")
    print()
    
    print("5. 프론트엔드에서 테스트해보세요!")

if __name__ == "__main__":
    print("📝 서울경제신문 프롬프트 테스트 도구")
    print("=" * 50)
    
    apply_test_prompts()
    
    print("\n💡 추가 팁:")
    print("- 각 에이전트별로 다른 스타일의 프롬프트를 테스트해보세요")
    print("- 이모지나 특수 기호를 활용해서 가독성을 높여보세요") 
    print("- 구체적인 지시사항을 추가해서 더 정확한 결과를 얻어보세요")
    print("- 제목 개수나 길이 제한 등을 명시해보세요")
    
    # 실제 프롬프트 내용 저장
    test_prompts = get_test_prompts()
    with open('/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/test_prompts.json', 'w', encoding='utf-8') as f:
        json.dump(test_prompts, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 테스트 프롬프트가 test_prompts.json에 저장되었습니다.")