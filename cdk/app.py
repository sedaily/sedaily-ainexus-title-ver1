#!/usr/bin/env python3
import aws_cdk as cdk
import os
from bedrock_stack import BedrockDiyStack
from frontend_stack import FrontendStack

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
        f"JournalismFaithfulStack{stack_suffix}",
        stack_name=f"JournalismFaithfulStack{stack_suffix}",
        description=f"저널리즘 충실형 제목 생성 시스템 - {domain_suffix.upper()} 환경",
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "JournalismFaithful",
            "Owner": "Development"
        }
    )

    # 2. 프론트엔드 스택 생성
    # 프로덕션 환경에 커스텀 도메인 설정
    custom_domain = None
    if domain_suffix == 'prod':
        custom_domain = "title-t5-v2.sedaily.io"
    
    frontend_stack = FrontendStack(
        app, 
        f"JournalismFaithfulFrontendStack{stack_suffix}",
        stack_name=f"JournalismFaithfulFrontendStack{stack_suffix}",
        api_gateway_url=backend_stack.api.url,
        rest_api=backend_stack.api,
        domain_name=custom_domain,  # 커스텀 도메인 설정
        stage=domain_suffix,  # 환경 정보 전달
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "JournalismFaithful",
            "Owner": "Development"
        }
    )

    # 스택 간 의존성 설정
    frontend_stack.add_dependency(backend_stack)

    print(f"✅ {domain_suffix.upper()} stacks configured:")
    print(f"   - Backend: JournalismFaithfulStack{stack_suffix}")
    print(f"   - Frontend: JournalismFaithfulFrontendStack{stack_suffix}")

app.synth() 