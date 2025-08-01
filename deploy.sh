#!/bin/bash

# 배포 스크립트
echo "🚀 Starting deployment..."

cd cdk

# 1. 프로덕션 환경 배포
echo "📦 Deploying Production stacks..."
cdk deploy BedrockDiyTitleGeneratorStack TitleGeneratorFrontendStack --require-approval never

# 2. 개발 환경 배포 (선택적)
# echo "📦 Deploying Development stacks..."
# cdk deploy BedrockDiyTitleGeneratorStackDev TitleGeneratorFrontendStackDev --require-approval never

echo "✅ Deployment completed!"