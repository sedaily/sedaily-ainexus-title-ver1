#!/usr/bin/env python3
"""
CDK 앱 템플릿 - 환경 변수 기반 동적 스택 생성
이 파일을 app.py로 사용하거나 참고하여 수정하세요
"""
import aws_cdk as cdk
import os
from pathlib import Path
from dotenv import load_dotenv
from bedrock_stack import BedrockDiyStack
from frontend_stack import FrontendStack

# 프로젝트 루트의 .env.local 파일 로드
env_path = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_path)

app = cdk.App()

# 환경 변수에서 설정 로드
PROJECT_NAME = os.getenv('PROJECT_NAME', 'my-service')
PROJECT_PREFIX = os.getenv('PROJECT_PREFIX', 'my-service')
STACK_PREFIX = os.getenv('STACK_PREFIX', 'MyService')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', app.node.try_get_context("account"))
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')

# CDK 환경 설정
env = cdk.Environment(
    account=AWS_ACCOUNT_ID,
    region=AWS_REGION
)

# 환경별 설정
env_config = {
    'dev': {
        'stack_suffix': 'Dev',
        'domain_suffix': 'dev',
        'custom_domain': None
    },
    'staging': {
        'stack_suffix': 'Staging',
        'domain_suffix': 'staging',
        'custom_domain': os.getenv('STAGING_DOMAIN')
    },
    'prod': {
        'stack_suffix': '',
        'domain_suffix': 'prod',
        'custom_domain': os.getenv('DOMAIN_NAME')
    }
}

# 환경별 배포 설정
environments = ['dev', 'prod']  # 필요한 환경만 선택

for env_name in environments:
    config = env_config.get(env_name, env_config['dev'])
    stack_suffix = config['stack_suffix']
    domain_suffix = config['domain_suffix']
    custom_domain = config['custom_domain']
    
    print(f"🚀 Creating {env_name.upper()} stacks for {PROJECT_NAME}")
    
    # 1. 백엔드 스택 생성
    backend_stack = BedrockDiyStack(
        app, 
        f"{STACK_PREFIX}Stack{stack_suffix}",
        stack_name=f"{STACK_PREFIX}Stack{stack_suffix}",
        description=f"{PROJECT_NAME} Backend - {env_name.upper()}",
        project_name=PROJECT_NAME,
        project_prefix=PROJECT_PREFIX,
        environment_name=env_name,
        env=env,
        tags={
            "Environment": env_name,
            "Project": PROJECT_NAME,
            "ManagedBy": "CDK"
        }
    )
    
    # 2. 프론트엔드 스택 생성
    frontend_stack = FrontendStack(
        app, 
        f"{STACK_PREFIX}FrontendStack{stack_suffix}",
        stack_name=f"{STACK_PREFIX}FrontendStack{stack_suffix}",
        api_gateway_url=backend_stack.api.url,
        rest_api=backend_stack.api,
        domain_name=custom_domain,
        stage=domain_suffix,
        project_name=PROJECT_NAME,
        project_prefix=PROJECT_PREFIX,
        env=env,
        tags={
            "Environment": env_name,
            "Project": PROJECT_NAME,
            "ManagedBy": "CDK"
        }
    )
    
    # 스택 간 의존성 설정
    frontend_stack.add_dependency(backend_stack)
    
    print(f"✅ {env_name.upper()} stacks configured:")
    print(f"   - Backend: {STACK_PREFIX}Stack{stack_suffix}")
    print(f"   - Frontend: {STACK_PREFIX}FrontendStack{stack_suffix}")

# 출력 정보 추가
cdk.CfnOutput(
    backend_stack, "ProjectInfo",
    value=f"Project: {PROJECT_NAME}, Environment: {ENVIRONMENT}",
    description="Project Information"
)

app.synth()