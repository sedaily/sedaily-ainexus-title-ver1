from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deployment,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    CfnOutput,
    RemovalPolicy,
    Duration,
    Size,
    Fn
)
from constructs import Construct
import os

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_gateway_url: str = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 버킷 생성 (정적 웹사이트 호스팅)
        self.website_bucket = s3.Bucket(
            self, "WebsiteBucket",
            bucket_name=f"title-nomics-frontend-{self.account}-{self.region}",
            public_read_access=False,  # CloudFront OAI 사용
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                    noncurrent_version_expiration=Duration.days(30)
                )
            ]
        )
        
        # CloudFront Origin Access Identity
        origin_access_identity = cloudfront.OriginAccessIdentity(
            self, "OAI",
            comment=f"OAI for {self.website_bucket.bucket_name}"
        )
        
        # S3 버킷 정책 - CloudFront만 접근 허용
        self.website_bucket.grant_read(origin_access_identity)
        
        # API Gateway URL 처리
        if api_gateway_url:
            # URL에서 도메인 추출 (https:// 제거)
            api_domain = api_gateway_url.replace("https://", "").replace("http://", "")
            if api_domain.endswith("/"):
                api_domain = api_domain[:-1]
        else:
            # 백엔드 스택에서 가져오기 (Cross-stack reference)
            try:
                api_domain = Fn.import_value("ApiGatewayDomain")
            except:
                api_domain = "api.example.com"  # 기본값
        
        # CloudFront 동작 설정
        behaviors = {
            # 정적 파일들은 캐싱
            "*.js": cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(
                    self.website_bucket,
                    origin_access_identity=origin_access_identity
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            ),
            "*.css": cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(
                    self.website_bucket,
                    origin_access_identity=origin_access_identity
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True
            )
        }
        
        # API 프록시 설정 (API Gateway가 있는 경우에만)
        if api_domain != "api.example.com":
            behaviors["/api/*"] = cloudfront.BehaviorOptions(
                origin=origins.HttpOrigin(
                    api_domain,
                    protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER
            )
        
        # CloudFront 배포
        self.distribution = cloudfront.Distribution(
            self, "Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(
                    self.website_bucket,
                    origin_access_identity=origin_access_identity
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                origin_request_policy=cloudfront.OriginRequestPolicy.CORS_S3_ORIGIN,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
                compress=True
            ),
            additional_behaviors=behaviors,
            default_root_object="index.html",
            error_responses=[
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
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # 비용 최적화
            enabled=True,
            comment="TITLE-NOMICS Frontend Distribution",
            minimum_protocol_version=cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021
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
        CfnOutput(
            self, "WebsiteURL",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="Frontend CloudFront URL",
            export_name="FrontendURL"
        )
        
        CfnOutput(
            self, "BucketName",
            value=self.website_bucket.bucket_name,
            description="S3 Bucket Name for Frontend",
            export_name="FrontendBucketName"
        )
        
        CfnOutput(
            self, "DistributionId",
            value=self.distribution.distribution_id,
            description="CloudFront Distribution ID",
            export_name="DistributionId"
        )
        
        CfnOutput(
            self, "DistributionDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
            export_name="DistributionDomainName"
        ) 