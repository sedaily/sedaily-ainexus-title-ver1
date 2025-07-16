from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_ssm as ssm,
    CfnOutput,
    RemovalPolicy,
    Duration
)
from constructs import Construct
import json

class CICDStack(Stack):
    """
    GitHub Actions 기반 CI/CD 파이프라인 스택
    프론트엔드 배포 자동화 및 백엔드 연동
    """
    
    def __init__(self, scope: Construct, construct_id: str, 
                 api_gateway_url: str = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.api_gateway_url = api_gateway_url
        
        # 1. 프론트엔드 배포 인프라
        self.create_frontend_infrastructure()
        
        # 2. CI/CD 지원 리소스
        self.create_cicd_resources()
        
        # 3. 보안 및 권한 설정
        self.setup_security()
        
        # 4. 출력값 생성
        self.create_outputs()
    
    def create_frontend_infrastructure(self):
        """프론트엔드 배포 인프라 생성"""
        
        # 1. S3 버킷 생성 (정적 웹사이트 호스팅)
        self.frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            bucket_name=f"dynamic-prompt-frontend-{self.account}-{self.region}",
            public_read_access=False,  # CloudFront OAI 사용
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioning=True,  # 버전 관리 활성화
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(30),
                    abort_incomplete_multipart_upload_after=Duration.days(7)
                )
            ]
        )
        
        # 2. CloudFront Origin Access Identity
        self.origin_access_identity = cloudfront.OriginAccessIdentity(
            self, "FrontendOAI",
            comment="OAI for Dynamic Prompt System frontend"
        )
        
        # 3. S3 버킷 정책 (CloudFront만 접근 허용)
        self.frontend_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[self.frontend_bucket.arn_for_objects("*")],
                principals=[self.origin_access_identity.grant_principal]
            )
        )
        
        # 4. CloudFront Distribution 생성
        self.create_cloudfront_distribution()
    
    def create_cloudfront_distribution(self):
        """CloudFront 배포 생성"""
        
        # API Gateway 프록시 설정
        api_behaviors = {}
        if self.api_gateway_url:
            api_domain = self.api_gateway_url.replace("https://", "").replace("http://", "")
            if api_domain.endswith("/"):
                api_domain = api_domain[:-1]
            
            api_behaviors = {
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        api_domain,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                        origin_path="/prod"  # API Gateway 스테이지
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    compress=True
                )
            }
        
        # CloudFront Distribution
        self.distribution = cloudfront.Distribution(
            self, "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(
                    self.frontend_bucket,
                    origin_access_identity=self.origin_access_identity
                ),
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            additional_behaviors=api_behaviors,
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(5)
                )
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # 비용 최적화
            geo_restriction=cloudfront.GeoRestriction.allowlist("KR", "US"),  # 한국, 미국만 허용
            enabled=True,
            comment="Dynamic Prompt System Frontend Distribution"
        )
    
    def create_cicd_resources(self):
        """CI/CD 지원 리소스 생성"""
        
        # 1. GitHub Actions용 IAM 역할
        self.github_actions_role = iam.Role(
            self, "GitHubActionsRole",
            role_name="dynamic-prompt-github-actions-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="GitHub Actions에서 사용하는 배포 역할",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # 2. S3 배포 권한
        self.frontend_bucket.grant_read_write(self.github_actions_role)
        
        # 3. CloudFront 캐시 무효화 권한
        self.github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudfront:CreateInvalidation",
                    "cloudfront:GetDistribution",
                    "cloudfront:GetDistributionConfig"
                ],
                resources=[f"arn:aws:cloudfront::{self.account}:distribution/{self.distribution.distribution_id}"]
            )
        )
        
        # 4. CDK 배포 권한 (백엔드 업데이트용)
        self.github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudformation:DescribeStacks",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:DescribeStackResources",
                    "cloudformation:GetTemplate",
                    "cloudformation:UpdateStack",
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:ListStacks"
                ],
                resources=[f"arn:aws:cloudformation:{self.region}:{self.account}:stack/BedrockDiyAuthStack/*"]
            )
        )
        
        # 5. Lambda 업데이트 권한
        self.github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "lambda:UpdateFunctionCode",
                    "lambda:UpdateFunctionConfiguration",
                    "lambda:GetFunction",
                    "lambda:ListFunctions"
                ],
                resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:bedrock-diy-*"]
            )
        )
        
        # 6. 배포 설정 저장용 Parameter Store
        self.deployment_config = ssm.StringParameter(
            self, "DeploymentConfig",
            parameter_name="/dynamic-prompt/deployment/config",
            string_value=json.dumps({
                "frontend_bucket": self.frontend_bucket.bucket_name,
                "cloudfront_distribution_id": self.distribution.distribution_id,
                "api_gateway_url": self.api_gateway_url or "https://api.dynamic-prompt.com",
                "region": self.region
            }),
            description="Dynamic Prompt System 배포 설정"
        )
        
        # 7. 배포 스크립트 생성
        self.create_deployment_scripts()
    
    def create_deployment_scripts(self):
        """배포 스크립트 생성"""
        
        # GitHub Actions 워크플로우 템플릿 (수정된 버전)
        self.github_workflow_template = {
            "name": "Deploy Dynamic Prompt System",
            "on": {
                "push": {
                    "branches": ["main"]
                },
                "pull_request": {
                    "branches": ["main"]
                }
            },
            "env": {
                "AWS_REGION": self.region,
                "NODE_VERSION": "18",
                "PYTHON_VERSION": "3.11"
            },
            "jobs": {
                "test": {
                    "name": "Test and Lint",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "${{ env.NODE_VERSION }}",
                                "cache": "npm",
                                "cache-dependency-path": "frontend/package-lock.json"
                            }
                        },
                        {
                            "name": "Install frontend dependencies",
                            "run": "cd frontend && npm ci"
                        },
                        {
                            "name": "Run frontend tests",
                            "run": "cd frontend && npm test -- --coverage --watchAll=false"
                        },
                        {
                            "name": "Run frontend lint",
                            "run": "cd frontend && npm run lint"
                        }
                    ]
                },
                "deploy": {
                    "name": "Deploy to AWS",
                    "runs-on": "ubuntu-latest",
                    "needs": "test",
                    "if": "github.ref == 'refs/heads/main'",
                    "steps": [
                        {
                            "name": "Checkout code",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "Configure AWS credentials",
                            "uses": "aws-actions/configure-aws-credentials@v4",
                            "with": {
                                "aws-access-key-id": "${{ secrets.AWS_ACCESS_KEY_ID }}",
                                "aws-secret-access-key": "${{ secrets.AWS_SECRET_ACCESS_KEY }}",
                                "aws-region": "${{ env.AWS_REGION }}"
                            }
                        },
                        {
                            "name": "Setup Node.js",
                            "uses": "actions/setup-node@v4",
                            "with": {
                                "node-version": "${{ env.NODE_VERSION }}",
                                "cache": "npm",
                                "cache-dependency-path": "frontend/package-lock.json"
                            }
                        },
                        {
                            "name": "Setup Python",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "${{ env.PYTHON_VERSION }}"
                            }
                        },
                        {
                            "name": "Install AWS CDK",
                            "run": "npm install -g aws-cdk"
                        },
                        {
                            "name": "Install CDK dependencies",
                            "run": "cd cdk && pip install -r requirements.txt"
                        },
                        {
                            "name": "Deploy backend",
                            "run": "cd cdk && cdk deploy BedrockDiyAuthStack --require-approval never"
                        },
                        {
                            "name": "Get API Gateway URL",
                            "id": "get-api-url",
                            "run": "API_URL=$(aws cloudformation describe-stacks --stack-name BedrockDiyAuthStack --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text)\necho \"api_url=$API_URL\" >> $GITHUB_OUTPUT"
                        },
                        {
                            "name": "Build frontend",
                            "run": "cd frontend\necho \"REACT_APP_API_URL=${{ steps.get-api-url.outputs.api_url }}\" > .env.production\nnpm ci\nnpm run build"
                        },
                        {
                            "name": "Deploy frontend to S3",
                            "run": f"aws s3 sync frontend/build/ s3://{self.frontend_bucket.bucket_name} --delete"
                        },
                        {
                            "name": "Invalidate CloudFront cache",
                            "run": f"aws cloudfront create-invalidation --distribution-id {self.distribution.distribution_id} --paths \"/*\""
                        }
                    ]
                }
            }
        }
        
        # 배포 스크립트 파일 생성 (권장사항)
        self.deployment_script_template = f"""#!/bin/bash

# Dynamic Prompt System 자동 배포 스크립트
# GitHub Actions에서 사용하거나 로컬에서 직접 실행 가능

set -e

# 환경 변수 설정
export AWS_REGION="{self.region}"
export FRONTEND_BUCKET="{self.frontend_bucket.bucket_name}"
export CLOUDFRONT_DISTRIBUTION_ID="{self.distribution.distribution_id}"

# 색상 정의
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

print_step() {{
    echo -e "${{BLUE}}=== $1 ===${{NC}}"
}}

print_success() {{
    echo -e "${{GREEN}}✅ $1${{NC}}"
}}

print_warning() {{
    echo -e "${{YELLOW}}⚠️ $1${{NC}}"
}}

print_error() {{
    echo -e "${{RED}}❌ $1${{NC}}"
}}

# 1. 백엔드 배포
print_step "백엔드 배포 시작"
cd cdk
pip install -r requirements.txt
cdk deploy BedrockDiyAuthStack --require-approval never
print_success "백엔드 배포 완료"

# 2. API Gateway URL 가져오기
print_step "API Gateway URL 조회"
API_URL=$(aws cloudformation describe-stacks \\
  --stack-name BedrockDiyAuthStack \\
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \\
  --output text)
print_success "API URL: $API_URL"

# 3. 프론트엔드 빌드
print_step "프론트엔드 빌드 시작"
cd ../frontend
echo "REACT_APP_API_URL=$API_URL" > .env.production
npm ci
npm run build
print_success "프론트엔드 빌드 완료"

# 4. S3 배포
print_step "S3 배포 시작"
aws s3 sync build/ s3://$FRONTEND_BUCKET --delete
print_success "S3 배포 완료"

# 5. CloudFront 캐시 무효화
print_step "CloudFront 캐시 무효화 시작"
INVALIDATION_ID=$(aws cloudfront create-invalidation \\
  --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \\
  --paths "/*" \\
  --query 'Invalidation.Id' \\
  --output text)
print_success "캐시 무효화 ID: $INVALIDATION_ID"

# 6. 배포 완료
print_step "배포 완료"
echo "Frontend URL: https://${{CLOUDFRONT_DISTRIBUTION_ID}}.cloudfront.net"
echo "API URL: $API_URL"
print_success "Dynamic Prompt System 배포가 성공적으로 완료되었습니다!"
"""
    
    def setup_security(self):
        """보안 및 권한 설정"""
        
        # 1. S3 버킷 보안 강화
        self.frontend_bucket.add_cors_rule(
            allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
            allowed_origins=["*"],
            allowed_headers=["*"],
            max_age=3600
        )
        
        # 2. CloudFront 보안 헤더
        self.security_headers_function = cloudfront.Function(
            self, "SecurityHeadersFunction",
            code=cloudfront.FunctionCode.from_inline("""
function handler(event) {
    var response = event.response;
    var headers = response.headers;
    
    // 보안 헤더 추가
    headers['strict-transport-security'] = { value: 'max-age=31536000; includeSubDomains' };
    headers['content-type-options'] = { value: 'nosniff' };
    headers['x-frame-options'] = { value: 'DENY' };
    headers['x-content-type-options'] = { value: 'nosniff' };
    headers['referrer-policy'] = { value: 'strict-origin-when-cross-origin' };
    headers['permissions-policy'] = { value: 'camera=(), microphone=(), geolocation=()' };
    
    return response;
}
            """),
            comment="Add security headers to responses"
        )
        
        # 3. 환경별 접근 제어 (개발/프로덕션)
        self.access_control_recommendations = {
            "development": {
                "cloudfront_geo_restriction": ["KR", "US"],
                "s3_bucket_policy": "restrictive",
                "api_gateway_throttling": {"burst": 100, "rate": 50}
            },
            "production": {
                "cloudfront_geo_restriction": ["KR"],
                "s3_bucket_policy": "very_restrictive",
                "api_gateway_throttling": {"burst": 1000, "rate": 500}
            }
        }
    
    def create_outputs(self):
        """출력값 생성"""
        
        CfnOutput(
            self, "FrontendBucketName",
            value=self.frontend_bucket.bucket_name,
            description="프론트엔드 S3 버킷 이름",
            export_name="FrontendBucketName"
        )
        
        CfnOutput(
            self, "CloudFrontDistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront 배포 ID",
            export_name="CloudFrontDistributionId"
        )
        
        CfnOutput(
            self, "CloudFrontURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="CloudFront 배포 URL",
            export_name="CloudFrontURL"
        )
        
        CfnOutput(
            self, "GitHubActionsRoleArn",
            value=self.github_actions_role.role_arn,
            description="GitHub Actions IAM 역할 ARN",
            export_name="GitHubActionsRoleArn"
        )
        
        CfnOutput(
            self, "DeploymentConfigParameter",
            value=self.deployment_config.parameter_name,
            description="배포 설정 Parameter Store 경로",
            export_name="DeploymentConfigParameter"
        )
        
        CfnOutput(
            self, "GitHubWorkflowTemplate",
            value=json.dumps(self.github_workflow_template, indent=2),
            description="GitHub Actions 워크플로우 템플릿 (JSON)",
            export_name="GitHubWorkflowTemplate"
        )
        
        CfnOutput(
            self, "DeploymentScriptTemplate",
            value=self.deployment_script_template,
            description="배포 스크립트 템플릿",
            export_name="DeploymentScriptTemplate"
        ) 