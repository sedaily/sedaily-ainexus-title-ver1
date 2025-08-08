import time
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_cloudwatch as cloudwatch,
    aws_cognito as cognito,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_event_sources,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct
import json

class BedrockDiyStack(Stack):
    
    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성 - 인증을 위해 복원"""
        # 사용자 풀 생성
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"{self.project_prefix}-users-{self.env_suffix}",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 사용자 풀 클라이언트 생성
        self.user_pool_client = self.user_pool.add_client(
            "WebClient",
            user_pool_client_name=f"{self.project_prefix}-web-client-{self.env_suffix}",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False,
            prevent_user_existence_errors=True,
            enable_token_revocation=True,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30)
        )

        # 관리자 그룹 생성
        self.admin_group = cognito.CfnUserPoolGroup(
            self, "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="관리자 그룹",
            precedence=1
        )
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 프로젝트 접두사 가져오기 (리소스 이름 구별용)
        self.project_prefix = self.node.try_get_context("project_prefix") or "myproject"
        self.project_name = self.node.try_get_context("project_name") or "Title Generator"
        
        # 환경 이름 설정 (DynamoDB 테이블 이름에 사용)
        if "Dev" in construct_id:
            self.env_suffix = "dev"
        else:
            self.env_suffix = "prod"

        # 1. Cognito 사용자 풀 생성 (인증을 위해 복원)
        self.create_cognito_user_pool()
        
        # 2. S3 버킷들 생성
        self.create_s3_buckets()
        
        # 3. DynamoDB 테이블들 생성 (프롬프트 관련 + 사용자 관리)
        self.create_dynamodb_tables()
        
        # 4. Lambda 함수들 생성
        self.create_lambda_functions()
        
        # 5. API Gateway 생성
        self.create_api_gateway()
        
        # 6. WebSocket API 설정 (실시간 스트리밍용)
        self.create_websocket_api()
        
        # 7. CloudWatch 알람 생성
        self.create_cloudwatch_alarms()
        
        # 8. SQS 큐 및 배치 처리 시스템 생성
        self.create_batch_processing_system()
        
        # 9. CDK 출력값 생성
        self.create_outputs()


    def create_s3_buckets(self):
        """S3 버킷들 생성 - 단순화됨"""
        # 프롬프트 저장용 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"{self.project_prefix}-prompts-{self.env_suffix}-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    max_age=3600
                )
            ]
        )

        # 기사 업로드용 버킷
        self.article_bucket = s3.Bucket(
            self, "ArticleBucket",
            bucket_name=f"{self.project_prefix}-articles-{self.env_suffix}-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    max_age=3600
                )
            ]
        )

    def create_dynamodb_tables(self):
        """DynamoDB 테이블 생성 - 필수 테이블만"""
        
        # =============================================================================
        # 프롬프트 관리 핵심 테이블
        # =============================================================================
        
        # 프롬프트 메타데이터 테이블 (관리자가 만든 프롬프트)
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name=f"{self.project_prefix}-prompt-meta-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="promptId",  # promptId를 파티션 키로 사용
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )


        # =============================================================================
        # 프롬프트 인스턴스 테이블
        # =============================================================================

        # 프롬프트 인스턴스 테이블 (사용자가 입력한 placeholder 값들)
        self.prompt_instance_table = dynamodb.Table(
            self, "PromptInstanceTable",
            table_name=f"{self.project_prefix}-prompt-instances-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="instanceId",  # instanceId를 파티션 키로 사용
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 사용자 관리 테이블 (인증을 위해 필요)
        self.users_table = dynamodb.Table(
            self, "UsersTable",
            table_name=f"{self.project_prefix}-users-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 이메일 인덱스 추가
        self.users_table.add_global_secondary_index(
            index_name="email-index",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        # 대화 관리 테이블
        self.conversations_table = dynamodb.Table(
            self, "ConversationsTable",
            table_name=f"{self.project_prefix}-conversations-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="conversation_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 사용자별 대화 조회를 위한 GSI
        self.conversations_table.add_global_secondary_index(
            index_name="user-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="created_at",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        # 메시지 관리 테이블
        self.messages_table = dynamodb.Table(
            self, "MessagesTable",
            table_name=f"{self.project_prefix}-messages-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="conversation_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )


    def create_lambda_functions(self):
        """Lambda 함수들 생성 - 필수 기능만"""
        # 공통 IAM 역할
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )

        # 필요한 리소스 권한만 추가
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject", 
                    "s3:DeleteObject",
                    "dynamodb:Query",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:GetItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    # Cognito 권한 추가
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminConfirmSignUp",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:AdminListGroupsForUser"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    self.article_bucket.bucket_arn,
                    self.article_bucket.bucket_arn + "/*",
                    self.prompt_meta_table.table_arn,
                    self.prompt_instance_table.table_arn,
                    self.users_table.table_arn,
                    self.users_table.table_arn + "/index/email-index",
                    # Cognito
                    self.user_pool.user_pool_arn,
                    f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{self.user_pool.user_pool_id}"
                ]
            )
        )

        # 1. 제목 생성 Lambda (핵심 기능) - 대용량 처리를 위해 메모리 증가
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.handler",
            code=lambda_.Code.from_asset("../lambda/generate"),
            timeout=Duration.minutes(15),
            memory_size=10240,  # 10GB로 증가 (최대 허용치)
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
            }
        )
        
        # 🔥 Lambda Response Streaming - 일단 주석 처리 (CloudFormation 미지원)
        # cfn_generate_function = self.generate_lambda.node.default_child
        # cfn_generate_function.add_property_override("InvokeConfig", {
        #     "InvokeMode": "RESPONSE_STREAM"
        # })

        # 2. 프롬프트 저장 Lambda
        self.save_prompt_lambda = lambda_.Function(
            self, "SavePromptFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="save_prompt.handler",
            code=lambda_.Code.from_asset("../lambda/save_prompt"),
            timeout=Duration.minutes(2),
            memory_size=512,
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
            }
        )
        
        # 3. 인증 관리 Lambda
        self.auth_lambda = lambda_.Function(
            self, "AuthFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="auth.handler",
            code=lambda_.Code.from_asset("../lambda/auth"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "USERS_TABLE": self.users_table.table_name,
                "REGION": self.region,
            }
        )
        
        # 4. JWT Authorizer Lambda
        self.jwt_authorizer_lambda = lambda_.Function(
            self, "JWTAuthorizerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="authorizer.handler",
            code=lambda_.Code.from_asset("../lambda/authorizer"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "REGION": self.region,
                "LOG_LEVEL": "INFO",
            }
        )
        
        # 4. 대화 관리 Lambda
        self.conversation_lambda = lambda_.Function(
            self, "ConversationFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="conversation_api.handler",
            code=lambda_.Code.from_asset("../lambda/conversation"),
            timeout=Duration.minutes(1),
            memory_size=512,
            role=lambda_role,
            environment={
                "CONVERSATIONS_TABLE": self.conversations_table.table_name,
                "USERS_TABLE": self.users_table.table_name,
                "REGION": self.region,
            }
        )
        
        # 5. 메시지 관리 Lambda
        self.message_lambda = lambda_.Function(
            self, "MessageFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="message_api.handler",
            code=lambda_.Code.from_asset("../lambda/message"),
            timeout=Duration.minutes(1),
            memory_size=512,
            role=lambda_role,
            environment={
                "MESSAGES_TABLE": self.messages_table.table_name,
                "CONVERSATIONS_TABLE": self.conversations_table.table_name,
                "REGION": self.region,
            }
        )

    # 간소화된 CORS 설정 함수
    def _create_cors_options_method(self, resource, allowed_methods):
        """CORS OPTIONS 메소드 생성 (간소화)"""
        return resource.add_method(
            "OPTIONS",
            apigateway.MockIntegration(
                integration_responses=[{
                    'statusCode': '200',
                    'responseParameters': {
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Methods': f"'{allowed_methods}'"
                    }
                }],
                request_templates={
                    'application/json': '{"statusCode": 200}'
                }
            ),
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Origin': True,
                    'method.response.header.Access-Control-Allow-Methods': True
                }
            }],
            authorization_type=apigateway.AuthorizationType.NONE
        )

    def create_api_gateway(self):
        """API Gateway 생성"""
        # REST API 생성
        self.api = apigateway.RestApi(
            self, "BedrockDiyApi",
            rest_api_name=f"{self.project_prefix}-api",
            description="제목 생성기 - 프롬프트 기반 AI 시스템",
            retain_deployments=True
        )

        # JWT Lambda Authorizer는 현재 사용하지 않음 (인증은 있지만 API Gateway에서는 비활성화)
        # self.api_authorizer = apigateway.TokenAuthorizer(
        #     self, "BedrockDiyApiAuthorizer",
        #     handler=self.jwt_authorizer_lambda,
        #     authorizer_name="title-generator-jwt-authorizer",
        #     results_cache_ttl=Duration.seconds(300)  # 5분 캐시
        # )

        # 인증 관련 경로 생성
        self.create_auth_routes()
        
        # 제목 생성 경로
        self.create_generate_routes()
        
        # 프롬프트 관리 경로
        self.create_prompt_routes()
        
        # /save-prompt endpoint (기존 호환성을 위해 유지)
        save_prompt_resource = self.api.root.add_resource("save-prompt")
        save_prompt_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        save_prompt_resource.add_method(
            "GET", 
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(save_prompt_resource, "GET,POST,OPTIONS")


    def create_auth_routes(self):
        """인증 관련 API 경로 생성"""
        auth_resource = self.api.root.add_resource("auth")
        
        # 인증 엔드포인트들
        auth_endpoints = ["signup", "signin", "refresh", "signout", "verify", "forgot-password", "confirm-password", "init-admin"]
        
        for endpoint in auth_endpoints:
            endpoint_resource = auth_resource.add_resource(endpoint)
            
            # POST 메소드 추가
            endpoint_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(self.auth_lambda, proxy=True),
                authorization_type=apigateway.AuthorizationType.NONE
            )
            
            # CORS 옵션 추가
            self._create_cors_options_method(endpoint_resource, "POST,OPTIONS")
    
    def create_generate_routes(self):
        """제목 생성 API 경로 생성"""
        # POST /generate (제목 생성)
        generate_resource = self.api.root.add_resource("generate")
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(generate_resource, "POST,OPTIONS")

    def create_prompt_routes(self):
        """프롬프트 관리 API 경로 생성"""
        prompts_resource = self.api.root.add_resource("prompts")
        
        # GET /prompts (프롬프트 카드 목록 조회)
        prompts_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # POST /prompts (새 프롬프트 카드 생성)
        prompts_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompts_resource, "GET,POST,OPTIONS")
        
        # /prompts/{promptId} 리소스
        prompt_card_resource = prompts_resource.add_resource("{promptId}")
        
        # GET /prompts/{promptId} (프롬프트 카드 상세 조회)
        prompt_card_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # PUT /prompts/{promptId} (프롬프트 카드 수정)
        prompt_card_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /prompts/{promptId} (프롬프트 카드 삭제)
        prompt_card_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompt_card_resource, "GET,PUT,DELETE,OPTIONS")
        
        # 대화 관리 API 경로 추가
        self.create_conversation_routes()

    def create_conversation_routes(self):
        """대화 관리 API 경로 생성"""
        # /conversations 리소스
        conversations_resource = self.api.root.add_resource("conversations")
        
        # GET /conversations (대화 목록 조회)
        conversations_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.conversation_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # POST /conversations (새 대화 생성)
        conversations_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.conversation_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(conversations_resource, "GET,POST,OPTIONS")
        
        # /conversations/{conversationId} 리소스
        conversation_detail_resource = conversations_resource.add_resource("{conversationId}")
        
        # GET /conversations/{conversationId} (대화 상세 조회)
        conversation_detail_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.conversation_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # PUT /conversations/{conversationId} (대화 수정)
        conversation_detail_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.conversation_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /conversations/{conversationId} (대화 삭제)
        conversation_detail_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.conversation_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(conversation_detail_resource, "GET,PUT,DELETE,OPTIONS")
        
        # /conversations/{conversationId}/messages 리소스
        messages_resource = conversation_detail_resource.add_resource("messages")
        
        # GET /conversations/{conversationId}/messages (메시지 목록 조회)
        messages_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.message_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # POST /conversations/{conversationId}/messages (새 메시지 추가)
        messages_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.message_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(messages_resource, "GET,POST,OPTIONS")

    # Step Functions 제거됨 - 단순화된 동적 프롬프트 시스템으로 불필요
    # def create_step_functions(self):
    #     """Step Functions 스테이트 머신 생성 - 제거됨"""
    #     pass

    def create_cloudwatch_alarms(self):
        """CloudWatch 알람 생성"""
        # Lambda 함수 오류율 알람
        lambda_funcs = [
            (self.generate_lambda, "Generate"),
            (self.save_prompt_lambda, "SavePrompt"),
            (self.websocket_stream_lambda, "WebSocketStream")
        ]
        
        for lambda_func, alarm_name in lambda_funcs:
            cloudwatch.Alarm(
                self, f"{alarm_name}ErrorAlarm",
                metric=lambda_func.metric_errors(period=Duration.minutes(5)),
                threshold=3,
                evaluation_periods=2,
                alarm_description=f"{alarm_name} Lambda 함수 오류율이 높습니다"
            )


    def create_outputs(self):
        """CDK 출력값 생성"""
        # API Gateway 출력
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name=f"{self.stack_name}-ApiUrl"
        )

        # S3 버킷 출력
        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름",
            export_name=f"{self.stack_name}-PromptBucketName"
        )
        
        CfnOutput(
            self, "ArticleBucketName",
            value=self.article_bucket.bucket_name,
            description="기사 S3 버킷 이름",
            export_name=f"{self.stack_name}-ArticleBucketName"
        )
        
        # Cognito 출력
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name=f"{self.stack_name}-UserPoolId"
        )

        CfnOutput(
            self, "UserPoolClientId", 
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name=f"{self.stack_name}-UserPoolClientId"
        )

    def create_websocket_api(self):
        """WebSocket API 생성 - 실시간 스트리밍용"""
        
        # WebSocket 연결 테이블
        self.websocket_connections_table = dynamodb.Table(
            self, "WebSocketConnectionsTable",
            table_name=f"{self.project_prefix}-websocket-connections-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="connectionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )
        
        # WebSocket Lambda 함수들용 공통 역할
        websocket_lambda_role = iam.Role(
            self, "WebSocketLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        # WebSocket 및 DynamoDB 권한 추가
        websocket_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "execute-api:ManageConnections",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "s3:GetObject",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*",
                    self.websocket_connections_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_bucket.bucket_arn + "/*"
                ]
            )
        )
        
        # Connect Lambda
        self.websocket_connect_lambda = lambda_.Function(
            self, "WebSocketConnectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="connect.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "REGION": self.region
            }
        )
        
        # Disconnect Lambda
        self.websocket_disconnect_lambda = lambda_.Function(
            self, "WebSocketDisconnectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="disconnect.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "REGION": self.region
            }
        )
        
        # Stream Lambda - 대용량 처리를 위해 메모리 증가
        self.websocket_stream_lambda = lambda_.Function(
            self, "WebSocketStreamFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="stream.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(15),
            memory_size=10240,  # 10GB로 증가 (최대 허용치)
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
                "USE_LANGGRAPH": "false",  # LangGraph 기능 비활성화 (우선 기본 스트리밍 테스트)
                "CONVERSATIONS_TABLE": self.conversations_table.table_name,
                "MESSAGES_TABLE": self.messages_table.table_name,
            }
        )
        
        # WebSocket API 생성
        self.websocket_api = apigatewayv2.WebSocketApi(
            self, "WebSocketApi",
            api_name=f"{self.project_prefix}-websocket-api",
            description="실시간 스트리밍을 위한 WebSocket API",
            connect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    self.websocket_connect_lambda
                )
            ),
            disconnect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration", 
                    self.websocket_disconnect_lambda
                )
            )
        )
        
        # Stream 라우트 추가
        self.websocket_api.add_route(
            "stream",
            integration=integrations.WebSocketLambdaIntegration(
                "StreamIntegration",
                self.websocket_stream_lambda
            )
        )
        
        # WebSocket API Stage 생성
        self.websocket_stage = apigatewayv2.WebSocketStage(
            self, "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name="prod",
            auto_deploy=True
        )
        
        # WebSocket API URL 출력 (stage 포함)
        websocket_url = f"{self.websocket_api.api_endpoint}/prod"
        CfnOutput(
            self, "WebSocketApiUrl",
            value=websocket_url,
            description="WebSocket API URL with stage",
            export_name=f"{self.stack_name}-WebSocketApiUrl"
        )

    def create_batch_processing_system(self):
        """대용량 문서 처리를 위한 SQS 및 배치 시스템 생성"""
        
        # 배치 작업 상태 추적 테이블
        self.batch_jobs_table = dynamodb.Table(
            self, "BatchJobsTable",
            table_name=f"{self.project_prefix}-batch-jobs-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="job_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )
        
        # 대용량 처리용 SQS 큐
        self.batch_queue = sqs.Queue(
            self, "BatchQueue",
            queue_name=f"{self.project_prefix}-batch-queue-{self.env_suffix}",
            visibility_timeout=Duration.minutes(15),
            receive_message_wait_time=Duration.seconds(20)
        )
        
        # 배치 처리 Lambda 역할
        batch_lambda_role = iam.Role(
            self, "BatchLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        # 배치 처리에 필요한 권한 추가
        batch_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:GetItem",
                    "s3:GetObject",
                    "bedrock:InvokeModel",
                    "execute-api:ManageConnections"
                ],
                resources=[
                    self.batch_queue.queue_arn,
                    self.batch_jobs_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*"
                ]
            )
        )
        
        # 기존 generate Lambda에 SQS 권한 추가
        self.generate_lambda.role.add_to_policy(
            iam.PolicyStatement(
                actions=["sqs:SendMessage", "dynamodb:PutItem"],
                resources=[self.batch_queue.queue_arn, self.batch_jobs_table.table_arn]
            )
        )
        
        # 환경 변수 추가
        self.generate_lambda.add_environment("BATCH_QUEUE_URL", self.batch_queue.queue_url)
        self.generate_lambda.add_environment("BATCH_JOBS_TABLE", self.batch_jobs_table.table_name)

 