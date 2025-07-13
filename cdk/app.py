#!/usr/bin/env python3
import aws_cdk as cdk
from bedrock_stack import BedrockDiyStack
from frontend_stack import FrontendStack
# from performance_optimization_stack import PerformanceOptimizationStack
# from cicd_stack import CICDStack

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# 1. 백엔드 스택 생성 (기존)
backend_stack = BedrockDiyStack(app, "BedrockDiyAuthStack",
    description="AWS Bedrock DIY Claude 프로젝트 백엔드 스택",
    env=env
)

# 2. 성능 최적화 스택 생성 (새로 추가) - 임시 주석 처리
# performance_stack = PerformanceOptimizationStack(app, "PerformanceOptimizationStack",
#     existing_lambdas={
#         "generate": backend_stack.generate_lambda,
#         "langchain_router": backend_stack.langchain_router_lambda,
#         "project": backend_stack.project_lambda,
#         "auth": backend_stack.auth_lambda,
#         "save_prompt": backend_stack.save_prompt_lambda
#     },
#     existing_api=backend_stack.api,
#     description="TITLE-NOMICS 성능 최적화 및 모니터링 스택",
#     env=env
# )

# 3. CI/CD 스택 생성 (새로 추가) - 임시 주석 처리
# cicd_stack = CICDStack(app, "CICDStack",
#     api_gateway_url=backend_stack.api.url,
#     description="TITLE-NOMICS CI/CD 파이프라인 스택",
#     env=env
# )

# 새로운 프론트엔드 스택 추가 - 임시 주석 처리
frontend_stack = FrontendStack(app, "FrontendStack", rest_api=backend_stack.api, env=env)

# 스택 간 의존성 설정
# frontend_stack.add_dependency(backend_stack)

app.synth() 