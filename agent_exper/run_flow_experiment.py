#!/usr/bin/env python3
"""
서울경제신문 Bedrock Flows 실험 실행 스크립트
"""

import os
import sys
import json
import asyncio
from seoul_economic_flow_manager import SeoulEconomicFlowManager

def setup_environment():
    """실험 환경 설정"""
    # AWS 자격 증명 확인 (boto3 세션으로)
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("⚠️ AWS 자격 증명을 찾을 수 없습니다.")
            print("AWS CLI를 설정하거나 환경 변수를 설정해주세요.")
            return False
        
        # STS로 현재 계정 확인
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS 환경 설정 완료 - Account: {identity['Account']}")
        return True
        
    except Exception as e:
        print(f"⚠️ AWS 환경 설정 오류: {str(e)}")
        return False

def load_existing_prompt_cards():
    """기존 프롬프트 카드 데이터 로드 (시뮬레이션)"""
    return {
        "planner": """
당신은 서울경제신문의 수석 편집 기획자입니다.

주요 역할:
- 기사의 핵심 메시지를 파악하여 전략적 제목 기획
- 독자의 관심을 끌 수 있는 구조적 제목 설계
- 신문의 브랜드 가치와 일치하는 제목 컨셉 제안

제목 작성 원칙:
1. 경제 뉴스의 핵심 포인트를 명확히 전달
2. 서울경제신문의 전문성을 보여주는 표현 사용
3. 독자의 궁금증을 유발하는 기획적 접근
4. 정확하고 신뢰할 수 있는 정보 전달

다음 내용에 대해 편집 기획자 관점에서 3개의 제목을 제안해주세요.
        """,
        
        "journalist": """
당신은 30년 경력의 서울경제신문 경제부 수석기자입니다.

전문 분야:
- 기업 경영, 금융, 증권, 부동산, 국제경제
- 정부 경제정책 및 시장 분석
- 산업 동향 및 기업 실적 분석

기사 작성 원칙:
1. 정확한 사실 기반의 제목 작성
2. 전문 용어의 적절한 활용
3. 독자가 이해하기 쉬운 명확한 표현
4. 뉴스의 중요도와 긴급성 반영

경험 많은 경제 전문기자로서 다음 내용에 대해 3개의 제목을 작성해주세요.
        """,
        
        "seo_expert": """
당신은 디지털 미디어 SEO 전문가입니다.

전문 영역:
- 검색엔진 최적화 전략
- 키워드 분석 및 적용
- 클릭률 향상 기법
- 소셜 미디어 확산 전략

SEO 최적화 원칙:
1. 주요 키워드를 제목 앞부분에 배치
2. 검색량이 높은 관련 키워드 포함
3. 20-60자 내의 최적 길이 유지
4. 명확하고 구체적인 정보 제공

검색 최적화 관점에서 다음 내용에 대해 3개의 제목을 제안해주세요.
        """,
        
        "social_strategist": """
당신은 소셜 미디어 마케팅 전문가입니다.

전문 분야:
- 소셜 플랫폼별 콘텐츠 최적화
- 바이럴 마케팅 전략
- 사용자 참여 유도 기법
- 트렌드 분석 및 활용

소셜 미디어 전략:
1. 공유하고 싶게 만드는 매력적 표현
2. 감정적 호소력이 있는 키워드 사용
3. 궁금증을 유발하는 질문형 제목
4. 트렌드 키워드의 자연스러운 활용

소셜 미디어에서 화제가 될 수 있는 관점에서 다음 내용에 대해 3개의 제목을 제안해주세요.
        """,
        
        "data_analyst": """
당신은 미디어 데이터 분석 전문가입니다.

분석 영역:
- 클릭률 데이터 분석
- 독자 행동 패턴 분석
- A/B 테스트 결과 해석
- 성과 지표 기반 최적화

데이터 기반 제목 원칙:
1. 과거 고성과 제목의 패턴 활용
2. 클릭률이 높은 키워드 조합 사용
3. 독자의 관심사와 검색 행동 반영
4. 시간대별, 요일별 최적화 고려

데이터 분석 결과를 바탕으로 다음 내용에 대해 클릭률이 높을 것으로 예상되는 3개의 제목을 제안해주세요.
        """
    }

async def run_flow_experiment():
    """Flow 실험 실행"""
    print("🚀 서울경제신문 Bedrock Flows 실험 시작")
    print("=" * 60)
    
    # 환경 설정 확인
    if not setup_environment():
        return False
    
    # Flow 매니저 초기화
    flow_manager = SeoulEconomicFlowManager()
    
    # 프롬프트 카드 로드
    prompt_cards = load_existing_prompt_cards()
    print(f"📋 프롬프트 카드 {len(prompt_cards)}개 로드 완료")
    
    try:
        # 1. Flow 생성
        print("\n🏗️  Flow 생성 중...")
        template_path = "/Users/yeong-gwang/Documents/work/서울경제신문/dev/nexus/title_generator_ver1/agent_exper/seoul_economic_multi_agent_flow.json"
        flow_id = flow_manager.create_flow_from_template(
            template_path, 
            "seoul-economic-title-generator-flow"
        )
        
        # 2. 에이전트 생성 (시간이 오래 걸리므로 선택적)
        create_agents = input("\n🤖 새로운 에이전트들을 생성하시겠습니까? (y/N): ").lower() == 'y'
        
        if create_agents:
            print("\n👥 에이전트 생성 중... (시간이 걸릴 수 있습니다)")
            agent_aliases = flow_manager.create_agents_for_flow(prompt_cards)
            
            if agent_aliases:
                print("🔗 Flow에 에이전트 연결 중...")
                flow_manager.update_flow_with_agents(flow_id, agent_aliases)
                
                print("📦 Flow 버전 준비 중...")
                version = flow_manager.prepare_flow_version(flow_id)
            else:
                print("⚠️ 에이전트 생성에 실패했습니다. 기존 설정을 사용합니다.")
        
        # 3. 테스트 실행
        print("\n🧪 Flow 테스트 실행")
        test_cases = [
            "삼성전자가 신형 갤럭시 스마트폰을 내년 1월 출시한다고 발표했습니다.",
            "한국은행이 기준금리를 0.25%포인트 인하하여 3.0%로 조정했습니다.",
            "네이버가 AI 검색 서비스를 대폭 개선하여 구글과의 경쟁을 본격화한다고 밝혔습니다."
        ]
        
        for i, test_input in enumerate(test_cases, 1):
            print(f"\n--- 테스트 케이스 {i} ---")
            print(f"입력: {test_input}")
            
            try:
                result = flow_manager.invoke_flow(flow_id, test_input)
                
                print("🎯 결과:")
                if result.get('outputs'):
                    for node_name, output in result['outputs'].items():
                        print(f"  {node_name}: {output}")
                
                if result.get('errors'):
                    print("❌ 오류:")
                    for error in result['errors']:
                        print(f"  {error}")
                        
            except Exception as e:
                print(f"❌ 테스트 {i} 실행 중 오류: {str(e)}")
        
        print("\n✅ Flow 실험 완료")
        print(f"🆔 생성된 Flow ID: {flow_id}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 실험 중 오류 발생: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("서울경제신문 Bedrock Flows 실험 도구")
    print("=" * 60)
    
    # 비동기 실행
    success = asyncio.run(run_flow_experiment())
    
    if success:
        print("\n🎉 실험이 성공적으로 완료되었습니다!")
        print("\n다음 단계:")
        print("1. 생성된 Flow를 CDK 스택에 통합")
        print("2. 프론트엔드에서 Flow 호출 기능 추가")
        print("3. 성능 모니터링 및 최적화")
    else:
        print("\n😞 실험 중 문제가 발생했습니다.")
        print("로그를 확인하고 다시 시도해주세요.")

if __name__ == "__main__":
    main()