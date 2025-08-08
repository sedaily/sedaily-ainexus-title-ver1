#!/usr/bin/env python3
import aws_cdk as cdk
import os

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
)

app.synth() 