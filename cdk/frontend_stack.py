from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigateway as apigateway,
    aws_s3_deployment as s3_deployment,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    CfnOutput,
    RemovalPolicy,
    Duration,
    Size,
    Fn,
    aws_iam
)
from constructs import Construct
import os
import urllib.parse

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_gateway_url: str | None = None, rest_api: apigateway.RestApi | None = None, domain_name: str | None = None, stage: str = "local", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 환경별 설정
        self.stage = stage
        self.domain_name = domain_name
        
        # 환경별 버킷 이름 생성 (고유성을 위해 계정 ID와 리전 추가)
        if stage == "prod":
            bucket_name = f"title-generator-frontend-prod-{self.account}-{self.region}"
            bucket_description = "Title Generator 프로덕션 프론트엔드"
        elif stage == "dev":
            bucket_name = f"title-generator-frontend-dev-{self.account}-{self.region}"
            bucket_description = "Title Generator 개발 프론트엔드"
        else:
            # local 환경
            bucket_name = f"title-generator-frontend-local-{self.account}-{self.region}"
            bucket_description = "Title Generator 로컬 개발 프론트엔드"
        
        print(f"🪣 Creating S3 bucket: {bucket_name} for {stage.upper()} environment")
        
        # S3 버킷 생성 (정적 웹사이트 호스팅)
        self.website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            bucket_name=bucket_name,
            public_read_access=False,  # CloudFront OAI 사용
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY if stage != "prod" else RemovalPolicy.RETAIN,
            auto_delete_objects=True if stage != "prod" else False,
            versioned=stage == "prod",  # 프로덕션에서만 버전 관리
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                    noncurrent_version_expiration=Duration.days(30) if stage == "prod" else Duration.days(7)
                )
            ]
        )
        
        # CloudFront Origin Access Control (OAC) - 새로운 권장 방식
        origin_access_control = cloudfront.S3OriginAccessControl(
            self, "OAC",
            origin_access_control_name=f"OAC-{self.website_bucket.bucket_name}",
            description=f"OAC for {self.website_bucket.bucket_name}",
            signing=cloudfront.Signing.SIGV4_ALWAYS
        )
        
        # S3 버킷 정책 - OAC가 S3에 접근할 수 있도록 허용
        self.website_bucket.add_to_resource_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                principals=[aws_iam.ServicePrincipal("cloudfront.amazonaws.com")],
                actions=["s3:GetObject"],
                resources=[self.website_bucket.arn_for_objects("*")],
                conditions={
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/*"
                    }
                }
            )
        )
        
        # API Gateway URL 처리
        api_origin_for_behavior = None
        if rest_api is not None:
            api_origin_for_behavior = origins.RestApiOrigin(
                rest_api,
                origin_path=f"/{rest_api.deployment_stage.stage_name}",
            )
            api_domain = "via-rest-api-object"
        else:
            origin_path = ""
            if api_gateway_url:
                parsed = urllib.parse.urlparse(api_gateway_url)
                api_domain = parsed.netloc or parsed.path
                origin_path = parsed.path if parsed.path not in ("", "/") else ""
                api_origin_for_behavior = origins.HttpOrigin(
                    api_domain,
                    origin_path=origin_path,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                )
            else:
                api_origin_for_behavior = None
        
        # CloudFront 동작 설정
        behaviors = {
            # 정적 파일들은 캐싱
            "*.js": cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.website_bucket,
                    origin_access_control=origin_access_control
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            "*.css": cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.website_bucket,
                    origin_access_control=origin_access_control
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            "/api/*": cloudfront.BehaviorOptions(
                origin=api_origin_for_behavior,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER
            )
        }
        
        # SSL 인증서 및 도메인 설정
        distribution_props = {
            "default_behavior": cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.website_bucket,
                    origin_access_control=origin_access_control
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
                compress=True
            ),
            "additional_behaviors": behaviors,
            "default_root_object": "index.html",
            "error_responses": [
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                )
            ],
            "price_class": cloudfront.PriceClass.PRICE_CLASS_100,
            "enabled": True,
            "comment": "Dynamic Prompt System Frontend Distribution",
            "minimum_protocol_version": cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021
        }
        
        # 커스텀 도메인이 설정된 경우 인증서와 도메인 추가
        if self.domain_name:
            try:
                # CloudFront는 us-east-1 리전의 인증서만 사용 가능
                # DNS 검증 인증서 생성 (us-east-1에 생성)
                certificate = acm.Certificate(
                    self, "Certificate",
                    domain_name=self.domain_name,
                    validation=acm.CertificateValidation.from_dns(),
                    region="us-east-1"  # CloudFront용 인증서는 반드시 us-east-1에 생성
                )
                
                # CloudFront에 도메인과 인증서 설정
                distribution_props["certificate"] = certificate
                distribution_props["domain_names"] = [self.domain_name]
                
                print(f"커스텀 도메인 설정: {self.domain_name}")
                
            except Exception as e:
                print(f"도메인 설정 실패, 기본 CloudFront 도메인 사용: {e}")
        
        # CloudFront 배포
        self.distribution = cloudfront.Distribution(
            self, "Distribution",
            **distribution_props
        )
        
        # 프론트엔드 빌드 파일이 있을 때만 배포
        if os.path.exists("../frontend/build"):
            s3_deployment.BucketDeployment(
                self, "DeployWebsite",
                sources=[s3_deployment.Source.asset("../frontend/build")],
                destination_bucket=self.website_bucket,
                distribution=self.distribution,
                distribution_paths=["/*"],
                retain_on_delete=False,
                memory_limit=512,
                ephemeral_storage_size=Size.mebibytes(512),
                prune=True  # 이전 파일 정리
            )
        
        # 출력값
        website_url = f"https://{self.domain_name}" if self.domain_name else f"https://{self.distribution.distribution_domain_name}"
        CfnOutput(
            self, "WebsiteURL",
            value=website_url,
            description="Frontend Website URL",
            export_name=f"{self.stack_name}-FrontendURL"
        )
        
        # 커스텀 도메인이 있는 경우 추가 출력
        if self.domain_name:
            CfnOutput(
                self, "CustomDomain",
                value=self.domain_name,
                description="Custom Domain Name",
                export_name=f"{self.stack_name}-CustomDomain"
            )
        
        CfnOutput(
            self, "BucketName",
            value=self.website_bucket.bucket_name,
            description="S3 Bucket Name for Frontend",
            export_name=f"{self.stack_name}-FrontendBucketName"
        )
        
        CfnOutput(
            self, "DistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront Distribution ID",
            export_name=f"{self.stack_name}-DistributionId"
        )
        
        CfnOutput(
            self, "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name=f"{self.stack_name}-DistributionDomainName"
        ) 