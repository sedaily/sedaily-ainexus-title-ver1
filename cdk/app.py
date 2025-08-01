#!/usr/bin/env python3
import aws_cdk as cdk
import os
from bedrock_stack import BedrockDiyStack
from frontend_stack import FrontendStack
# from conversation_stack import ConversationStack  # 제거: 대화 저장 기능 불필요
# from performance_optimization_stack import PerformanceOptimizationStack
# from cicd_stack import CICDStack

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region="ap-northeast-2"  # 서울 리전으로 고정
)

# 🔧 환경별 배포 설정
# 로컬 개발 스택('')은 CI/CD에서 중복 리소스 충돌을 일으키므로 제외
environments = ['Prod', 'Dev']  # 프로덕션, 개발

for suffix in environments:
    if suffix == '':
        # 로컬 개발용 (기본)
        stack_suffix = ''
        domain_suffix = 'local'
        print("🏠 Creating LOCAL development stacks")
    elif suffix == 'Prod':
        # 프로덕션 환경은 기존 스택 이름을 재사용(빈 접미사)
        stack_suffix = ''
        domain_suffix = 'prod'
        print("🚀 Creating PRODUCTION stacks")
    elif suffix == 'Dev':
        # 개발 환경
        stack_suffix = suffix
        domain_suffix = 'dev'
        print("🧪 Creating DEVELOPMENT stacks")
    else:
        continue

    # 1. 백엔드 스택 생성
    backend_stack = BedrockDiyStack(
        app, 
        f"BedrockDiyTitleGeneratorStack{stack_suffix}",
        stack_name=f"BedrockDiyTitleGeneratorStack{stack_suffix}",
        description=f"AWS Bedrock DIY 제목 생성기 시스템 - {domain_suffix.upper()} 환경",
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "TitleGenerator",
            "Owner": "CI/CD"
        }
    )

    # ConversationStack 제거 - 대화 저장 기능 불필요

    # 3. 프론트엔드 스택 생성
    frontend_stack = FrontendStack(
        app, 
        f"TitleGeneratorFrontendStack{stack_suffix}",
        stack_name=f"TitleGeneratorFrontendStack{stack_suffix}",
        api_gateway_url=backend_stack.api.url,
        rest_api=backend_stack.api,
        stage=domain_suffix,  # 환경 정보 전달
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "TitleGenerator",
            "Owner": "CI/CD"
        }
    )

    # 스택 간 의존성 설정
    frontend_stack.add_dependency(backend_stack)

    print(f"✅ {domain_suffix.upper()} stacks configured:")
    print(f"   - Backend: BedrockDiyTitleGeneratorStack{stack_suffix}")
    print(f"   - Frontend: TitleGeneratorFrontendStack{stack_suffix}")

app.synth() 