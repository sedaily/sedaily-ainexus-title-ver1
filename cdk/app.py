#!/usr/bin/env python3
import aws_cdk as cdk
from bedrock_stack import BedrockDiyStack
from frontend_stack import FrontendStack
from conversation_stack import ConversationStack
# from performance_optimization_stack import PerformanceOptimizationStack
# from cicd_stack import CICDStack

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1"
)

# 1. 백엔드 스택 생성 (단순화된 "빈깡통" 시스템)
backend_stack = BedrockDiyStack(app, "BedrockDiyTitleGeneratorStack",
    description="AWS Bedrock DIY 제목 생성기 시스템 - 인증 포함",
    env=env
)

# 1.5. 대화 기록 스택 생성
conversation_stack = ConversationStack(app, "ConversationStack",
    description="대화 기록 관리 시스템 - DynamoDB 및 Lambda",
    env=env
)

# 대화 API를 기존 API Gateway에 추가
conversation_stack.add_api_endpoints(backend_stack.api, backend_stack.api_authorizer)

# 2. 성능 최적화 스택 생성 (필요시 활성화)
# performance_stack = PerformanceOptimizationStack(app, "PerformanceOptimizationStack",
#     existing_lambdas={
#         "generate": backend_stack.generate_lambda,
#         "project": backend_stack.project_lambda,
#         "auth": backend_stack.auth_lambda,
#         "save_prompt": backend_stack.save_prompt_lambda
#     },
#     existing_api=backend_stack.api,
#     description="동적 프롬프트 시스템 성능 최적화 및 모니터링 스택",
#     env=env
# )

# 3. CI/CD 스택 생성 (필요시 활성화)
# cicd_stack = CICDStack(app, "CICDStack",
#     api_gateway_url=backend_stack.api.url,
#     description="동적 프롬프트 시스템 CI/CD 파이프라인 스택",
#     env=env
# )

# 4. 프론트엔드 스택 활성화 - S3 + CloudFront 정적 호스팅
frontend_stack = FrontendStack(app, "TitleGeneratorFrontendStack", 
    api_gateway_url=backend_stack.api.url,
    rest_api=backend_stack.api,
    # domain_name="titlenomics.com",  # 추후 도메인 구매 시 활성화
    env=env
)

# 스택 간 의존성 설정
# conversation_stack.add_dependency(backend_stack)  # 순환 참조 제거
frontend_stack.add_dependency(backend_stack)
frontend_stack.add_dependency(conversation_stack)

app.synth() 