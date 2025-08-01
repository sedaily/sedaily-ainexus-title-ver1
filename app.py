#!/usr/bin/env python3
import aws_cdk as cdk
import os

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

print("🚀 서울경제신문 AI 제목 생성기 v2")
print("✅ CDK 앱이 준비되었습니다!")
print("📝 다음 단계: 필요한 스택들을 추가하세요")

app.synth() 