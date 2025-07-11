#!/usr/bin/env python3
import aws_cdk as cdk
from cdk.bedrock_stack import BedrockDiyStack

app = cdk.App()

# 메인 스택 생성
BedrockDiyStack(app, "BedrockDiyStack",
    description="AWS Bedrock DIY Claude 프로젝트 스택",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth() 