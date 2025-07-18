from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_s3_notifications as s3_notifications,
    aws_cloudwatch as cloudwatch,
    aws_stepfunctions as stepfunctions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_budgets as budgets,
    aws_bedrock as bedrock,
    aws_sqs as sqs,
    aws_cognito as cognito,
    aws_ec2 as ec2,
    RemovalPolicy,
    Duration,
    CfnOutput,
    BundlingOptions
)
from constructs import Construct
import json

class BedrockDiyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Cognito 사용자 풀 생성
        self.create_cognito_user_pool()
        
        # 2. S3 버킷들 생성
        self.create_s3_buckets()
        
        # 3. DynamoDB 테이블들 생성
        self.create_dynamodb_tables()
        
        # 4. SQS DLQ 생성
        self.create_sqs_dlq()
        
        # 5. SNS 토픽 생성
        self.create_sns_topics()
        
        # 6. Bedrock Guardrail 생성
        self.create_bedrock_guardrail()
        
        # 7. Lambda 함수들 생성
        self.create_lambda_functions()
        
        # 8. API Gateway 생성
        self.create_api_gateway()
        
        # WebSocket API 설정
        self.create_websocket_api()
        
        # 9. CloudWatch 알람 생성
        self.create_cloudwatch_alarms()
        
        # 10. 비용 알람 생성
        # self.create_budget_alarms()  # 권한 문제로 임시 비활성화
        
        # 11. CDK 출력값 생성
        self.create_outputs()

    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성"""
        # 사용자 풀 생성
        self.user_pool = cognito.UserPool(
            self, "BedrockDiyUserPool",
            user_pool_name="bedrock-diy-users",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                fullname=cognito.StandardAttribute(
                    required=False,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=False,
                require_uppercase=False,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 사용자 풀 클라이언트 생성
        self.user_pool_client = self.user_pool.add_client(
            "BedrockDiyWebClient",
            user_pool_client_name="bedrock-diy-web-client",
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

        # 사용자 풀 도메인 생성 (선택사항 - Hosted UI를 사용할 경우)
        self.user_pool_domain = self.user_pool.add_domain(
            "BedrockDiyDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"bedrock-diy-{self.account}"
            )
        )

    def create_s3_buckets(self):
        """S3 버킷들 생성 - 단순화됨"""
        # 프롬프트 저장용 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"bedrock-diy-prompts-{self.account}-{self.region}",
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
            bucket_name=f"bedrock-diy-articles-{self.account}-{self.region}",
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
        """DynamoDB 테이블 생성"""
        # 프로젝트 메타데이터 테이블
        self.project_table = dynamodb.Table(
            self, "ProjectTable",
            table_name="bedrock-diy-projects-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )

        # 프롬프트 메타데이터 테이블 (확장)
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name="bedrock-diy-prompt-meta-v2-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="promptId",  # UUID 기반 promptId로 변경
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # GSI: step_order 기반 정렬을 위한 인덱스
        self.prompt_meta_table.add_global_secondary_index(
            index_name="projectId-stepOrder-index",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="stepOrder",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 대화/생성 기록 테이블
        self.conversation_table = dynamodb.Table(
            self, "ConversationTable",
            table_name="bedrock-diy-conversations-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Step Functions 실행 결과 테이블
        self.execution_table = dynamodb.Table(
            self, "ExecutionTable",
            table_name="bedrock-diy-executions-auth",
            partition_key=dynamodb.Attribute(
                name="executionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

    def create_sqs_dlq(self):
        """SQS DLQ 생성"""
        self.dlq = sqs.Queue(
            self, "IndexPromptDLQ",
            queue_name="bedrock-diy-index-prompt-dlq-auth",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # 메인 큐 (S3 이벤트 재시도용)
        self.index_queue = sqs.Queue(
            self, "IndexPromptQueue", 
            queue_name="bedrock-diy-index-prompt-auth",
            visibility_timeout=Duration.minutes(5),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.dlq
            )
        )

    def create_sns_topics(self):
        """SNS 토픽 생성"""
        self.completion_topic = sns.Topic(
            self, "CompletionTopic",
            topic_name="bedrock-diy-completion-auth"
        )

        self.error_topic = sns.Topic(
            self, "ErrorTopic", 
            topic_name="bedrock-diy-errors-auth"
        )

    def create_bedrock_guardrail(self):
        """Bedrock Guardrail 생성 - 단순화됨"""
        
        # Agent용 IAM 역할 (OpenSearch 없이)
        self.agent_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        # Knowledge Base용 IAM 역할 (OpenSearch 없이)
        self.kb_role = iam.Role(
            self, "BedrockKnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn,
                    f"{self.prompt_bucket.bucket_arn}/*"
                ]
            )
        )
        
        # Bedrock Agent 생성 (Knowledge Base 없이)
        self.bedrock_agent = bedrock.CfnAgent(
            self, "DynamicPromptAgent",
            agent_name="dynamic-prompt-system-agent",
            description="동적 프롬프트 시스템 AI 어시스턴트",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            agent_resource_role_arn=self.agent_role.role_arn,
            idle_session_ttl_in_seconds=1800,  # 30분
            instruction="당신은 동적 프롬프트 시스템의 AI 어시스턴트입니다. 사용자가 제공하는 프롬프트 카드의 내용에 따라 다양한 작업을 수행하며, 창의적이고 정확한 응답을 제공합니다. 항상 한국어로 응답하고, 사용자의 요청에 맞춰 유연하게 대응하세요."
        )
        
        # Agent Alias 생성 (배포용)
        self.agent_alias = bedrock.CfnAgentAlias(
            self, "DynamicPromptAgentAlias",
            agent_alias_name="production",
            agent_id=self.bedrock_agent.attr_agent_id,
            description="Production alias for Dynamic Prompt System agent"
        )

    def create_lambda_functions(self):
        """Lambda 함수들 생성 - 단순화됨"""
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
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sns:Publish",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminConfirmSignUp",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminRespondToAuthChallenge",
                    "cognito-idp:ConfirmForgotPassword",
                    "cognito-idp:ForgotPassword",
                    "cognito-idp:ConfirmSignUp",
                    "cognito-idp:ResendConfirmationCode"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    self.article_bucket.bucket_arn,
                    self.article_bucket.bucket_arn + "/*",
                    self.project_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_meta_table.table_arn + "/index/projectId-stepOrder-index",
                    self.conversation_table.table_arn,
                    self.execution_table.table_arn,
                    self.dlq.queue_arn,
                    self.index_queue.queue_arn,
                    self.completion_topic.topic_arn,
                    self.error_topic.topic_arn,
                    # 🔧 수정: Cognito User Pool ARN 추가
                    self.user_pool.user_pool_arn,
                    f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{self.user_pool.user_pool_id}"
                ]
            )
        )

        # 1. 제목 생성 Lambda (핵심 기능) - 최대 성능 설정 + 스트리밍 활성화
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.handler",
            # 🔧 강제 재배포를 위해 코드 자산을 명시적으로 지정
            code=lambda_.Code.from_asset("../lambda/generate"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "EXECUTION_TABLE": self.execution_table.table_name,
                "REGION": self.region,
            },
            dead_letter_queue=self.dlq
        )
        
        # 🔥 Lambda Response Streaming - 일단 주석 처리 (CloudFormation 미지원)
        # cfn_generate_function = self.generate_lambda.node.default_child
        # cfn_generate_function.add_property_override("InvokeConfig", {
        #     "InvokeMode": "RESPONSE_STREAM"
        # })

        # 2. 프롬프트 저장 Lambda (단순화됨)
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

        # 3. 프로젝트 관리 Lambda
        self.project_lambda = lambda_.Function(
            self, "ProjectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="project.handler",
            code=lambda_.Code.from_asset("../lambda/project"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "PROJECT_TABLE": self.project_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
            }
        )

        # 4. 인증 관리 Lambda
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
        """API Gateway 생성 - 간소화된 버전"""
        # REST API 생성
        self.api = apigateway.RestApi(
            self, "BedrockDiyApi",
            rest_api_name="bedrock-diy-api",
            description="동적 프롬프트 시스템 - 완전한 빈깡통 AI",
            retain_deployments=True
        )

        # Cognito Authorizer 생성
        self.api_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "BedrockDiyApiAuthorizer",
            cognito_user_pools=[self.user_pool],
            authorizer_name="bedrock-diy-authorizer",
            identity_source="method.request.header.Authorization"
        )

        # 인증 관련 경로 생성
        self.create_auth_routes()
        
        # 프로젝트 관련 경로 생성
        self.create_project_routes()
        
        # 프롬프트 관리 경로 생성
        self.create_prompt_routes()
        
        # 스트리밍 엔드포인트 추가
        projects_resource = self.api.root.get_resource("projects")
        project_resource = projects_resource.get_resource("{projectId}")
        
        # 스트리밍 리소스 생성
        generate_resource = project_resource.get_resource("generate")
        stream_resource = generate_resource.add_resource("stream")
        
        # 스트리밍 메서드 추가 (간소화된 설정)
        stream_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(stream_resource, "OPTIONS,POST")

    def create_auth_routes(self):
        """인증 관련 API 경로 생성"""
        auth_resource = self.api.root.add_resource("auth")
        
        # 인증 엔드포인트들
        auth_endpoints = ["signup", "signin", "refresh", "signout", "verify", "forgot-password", "confirm-password"]
        
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

    def create_project_routes(self):
        """프로젝트 관련 API 경로 생성"""
        projects_resource = self.api.root.add_resource("projects")
        
        # POST /projects (프로젝트 생성)
        projects_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # GET /projects (프로젝트 목록)
        projects_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(projects_resource, "GET,POST,PUT,DELETE,OPTIONS")

        # /projects/{id} 리소스
        project_resource = projects_resource.add_resource("{projectId}")
        
        # GET /projects/{id} (프로젝트 상세)
        project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # PUT /projects/{id} (프로젝트 수정)
        project_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /projects/{id} (프로젝트 삭제)
        project_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(project_resource, "GET,POST,PUT,DELETE,OPTIONS")

        # POST /projects/{id}/generate (제목 생성)
        generate_resource = project_resource.add_resource("generate")
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(generate_resource, "POST,OPTIONS")

        # GET /projects/{id}/upload-url (파일 업로드용 pre-signed URL)
        upload_url_resource = project_resource.add_resource("upload-url")
        upload_url_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(upload_url_resource, "GET,OPTIONS")

    def create_prompt_routes(self):
        """프롬프트 관리 API 경로 생성"""
        prompts_resource = self.api.root.add_resource("prompts")
        prompts_project_resource = prompts_resource.add_resource("{projectId}")
        
        # POST /prompts/{projectId} (새 프롬프트 카드 생성)
        prompts_project_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # GET /prompts/{projectId} (프롬프트 카드 목록 조회)
        prompts_project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompts_project_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{projectId}/{promptId} 리소스
        prompt_card_resource = prompts_project_resource.add_resource("{promptId}")
        
        # PUT /prompts/{projectId}/{promptId} (프롬프트 카드 수정)
        prompt_card_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /prompts/{projectId}/{promptId} (프롬프트 카드 삭제)
        prompt_card_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompt_card_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{projectId}/{promptId}/content 리소스 추가
        content_resource = prompt_card_resource.add_resource("content")
        
        # GET /prompts/{projectId}/{promptId}/content (프롬프트 내용 조회)
        content_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(content_resource, "GET,OPTIONS")

    # Step Functions 제거됨 - 단순화된 동적 프롬프트 시스템으로 불필요
    # def create_step_functions(self):
    #     """Step Functions 스테이트 머신 생성 - 제거됨"""
    #     pass

    def create_cloudwatch_alarms(self):
        """CloudWatch 알람 생성"""
        # Lambda 함수 오류율 알람
        lambda_funcs = [
            (self.generate_lambda, "Generate"),
            (self.project_lambda, "Project"),
            (self.save_prompt_lambda, "SavePrompt"),
            (self.auth_lambda, "Auth")
        ]
        
        for lambda_func, alarm_name in lambda_funcs:
            cloudwatch.Alarm(
                self, f"{alarm_name}ErrorAlarm",
                metric=lambda_func.metric_errors(period=Duration.minutes(5)),
                threshold=3,
                evaluation_periods=2,
                alarm_description=f"{alarm_name} Lambda 함수 오류율이 높습니다"
            )

        # DLQ 메시지 알람
        cloudwatch.Alarm(
            self, "DLQMessageAlarm",
            metric=self.dlq.metric("ApproximateNumberOfVisibleMessages"),
            threshold=1,
            evaluation_periods=1,
            alarm_description="DLQ에 메시지가 있습니다"
        )

    def create_budget_alarms(self):
        """비용 알람 생성 - 권한 문제로 임시 비활성화"""
        pass
        # 월 $1000 예산 알람
        # budgets.CfnBudget(
        #     self, "MonthlyBudget",
        #     budget=budgets.CfnBudget.BudgetDataProperty(
        #         budget_name="bedrock-diy-monthly-budget",
        #         budget_type="COST",
        #         budget_limit=budgets.CfnBudget.SpendProperty(
        #             amount=1000,
        #             unit="USD"
        #         ),
        #         time_unit="MONTHLY",
        #         cost_filters={
        #             "Service": ["Amazon Bedrock", "AWS Lambda"]  # 🔧 수정: OpenSearch 제거
        #         }
        #     ),
        #     notifications_with_subscribers=[
        #         budgets.CfnBudget.NotificationWithSubscribersProperty(
        #             notification=budgets.CfnBudget.NotificationProperty(
        #                 notification_type="ACTUAL",
        #                 comparison_operator="GREATER_THAN",
        #                 threshold=80
        #             ),
        #             subscribers=[
        #                 # 🔧 수정: 더미 이메일 제거 - 실제 사용 시 환경변수나 파라미터로 설정
        #                 # budgets.CfnBudget.SubscriberProperty(
        #                 #     subscription_type="EMAIL",
        #                 #     address="admin@example.com"
        #                 # )
        #             ]
        #         )
        #     ]
        # )

    def create_outputs(self):
        """CDK 출력값 생성"""
        # 중요: API Gateway 출력
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name="BedrockDiyApiUrl"
        )

        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름",
            export_name="PromptBucketName"
        )

        # 🔧 추가: 중요한 리소스 출력값들 추가
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="UserPoolId"
        )

        CfnOutput(
            self, "UserPoolClientId", 
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="UserPoolClientId"
        )

    def create_websocket_api(self):
        """WebSocket API 생성 - 실시간 스트리밍용"""
        
        # WebSocket 연결 테이블
        self.websocket_connections_table = dynamodb.Table(
            self, "WebSocketConnectionsTable",
            table_name="bedrock-diy-websocket-connections",
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
        
        # Stream Lambda
        self.websocket_stream_lambda = lambda_.Function(
            self, "WebSocketStreamFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="stream.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region
            }
        )
        
        # WebSocket API 생성
        self.websocket_api = apigatewayv2.WebSocketApi(
            self, "BedrockDiyWebSocketApi",
            api_name="bedrock-diy-websocket-api",
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
            export_name="WebSocketApiUrl"
        ) 