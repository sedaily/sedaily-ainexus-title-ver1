from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_opensearchservice as opensearch,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
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
    RemovalPolicy,
    Duration,
    CfnOutput
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
        
        # 4. OpenSearch 도메인 생성 (임시 비활성화 - Agent만 먼저 구현)
        # self.create_opensearch_domain()
        
        # 5. SQS DLQ 생성
        self.create_sqs_dlq()
        
        # 6. SNS 토픽 생성
        self.create_sns_topics()
        
        # 7. Bedrock Guardrail 생성
        self.create_bedrock_guardrail()
        
        # 7.5. Bedrock Agent 및 Knowledge Base 생성
        self.create_bedrock_agent_and_kb()
        
        # 8. Lambda 함수들 생성
        self.create_lambda_functions()
        
        # 9. Step Functions 생성 (임시 비활성화)
        # self.create_step_functions()
        
        # 10. API Gateway 생성
        self.create_api_gateway()
        
        # 11. S3 이벤트 트리거 설정 (현재 비활성화)
        # self.setup_s3_triggers()
        
        # 12. CloudWatch 알람 설정 (강화)
        self.create_cloudwatch_alarms()
        
        # 13. 비용 알람 설정 (권한 없음으로 비활성화)
        # self.create_budget_alarms()
        
        # 14. CDK 출력값 생성
        self.create_outputs()

    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성"""
        # 사용자 풀 생성
        self.user_pool = cognito.UserPool(
            self, "BedrockDiyUserPool",
            user_pool_name="bedrock-diy-users",
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
                ),
                fullname=cognito.StandardAttribute(
                    required=False,
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
        """S3 버킷 생성"""
        # 프롬프트 파일 저장용 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"bedrock-diy-prompts-auth-{self.account}-{self.region}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                allowed_origins=["*"],
                allowed_headers=["*"],
                max_age=3000
            )],
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90)
                        )
                    ]
                )
            ]
        )

        # 기사 임시 저장용 버킷
        self.article_bucket = s3.Bucket(
            self, "ArticleBucket",
            bucket_name=f"bedrock-diy-articles-auth-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(30)  # 30일 후 자동 삭제
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
                name="executionArn",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # 🆕 채팅 히스토리 테이블 (LangChain용)
        self.chat_history_table = dynamodb.Table(
            self, "ChatHistoryTable",
            table_name="bedrock-diy-chat-history-auth",
            partition_key=dynamodb.Attribute(
                name="pk",  # projectId#userId
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk",  # TS#<epoch>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"  # 90일 후 자동 삭제
        )

        # GSI for recent messages query
        self.chat_history_table.add_global_secondary_index(
            index_name="role-timestamp-index",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 🆕 채팅 세션 메타데이터 테이블
        self.chat_session_table = dynamodb.Table(
            self, "ChatSessionTable",
            table_name="bedrock-diy-chat-sessions-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sessionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

    def create_opensearch_domain(self):
        """OpenSearch 도메인 생성"""
        self.opensearch_domain = opensearch.Domain(
            self, "OpenSearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_5,
            domain_name="bedrock-diy-search",
            capacity=opensearch.CapacityConfig(
                data_nodes=1,
                data_node_instance_type="t3.small.search",
                master_nodes=0
            ),
            ebs=opensearch.EbsOptions(
                volume_size=10,
                volume_type="gp3"
            ),
            zone_awareness=opensearch.ZoneAwarenessConfig(
                enabled=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            # 개발 환경용 - 프로덕션에서는 VPC 내부에 배치
            access_policies=[
                iam.PolicyStatement(
                    actions=["es:*"],
                    principals=[iam.ArnPrincipal("*")],
                    resources=["*"]
                )
            ]
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
        """Bedrock Guardrail 생성"""
        self.guardrail = bedrock.CfnGuardrail(
            self, "ProjectGuardrail",
            name="bedrock-diy-guardrail",
            description="TITLE-NOMICS 프로젝트 기본 가드레일",
            blocked_input_messaging="입력 내용이 가이드라인을 위반합니다.",
            blocked_outputs_messaging="생성된 콘텐츠가 가이드라인을 위반합니다.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="HIGH",
                        type="HATE"
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="HIGH", 
                        type="VIOLENCE"
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="MEDIUM",
                        output_strength="MEDIUM",
                        type="SEXUAL"
                    ),
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        input_strength="HIGH",
                        output_strength="HIGH",
                        type="MISCONDUCT"
                    )
                ]
            ),
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="BLOCK",
                        type="EMAIL"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="BLOCK",
                        type="PHONE"
                    ),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(
                        action="BLOCK",
                        type="CREDIT_DEBIT_CARD_NUMBER"
                    )
                ]
            ),
            word_policy_config=bedrock.CfnGuardrail.WordPolicyConfigProperty(
                words_config=[
                    bedrock.CfnGuardrail.WordConfigProperty(
                        text="password"
                    ),
                    bedrock.CfnGuardrail.WordConfigProperty(
                        text="secret"
                    ),
                    bedrock.CfnGuardrail.WordConfigProperty(
                        text="token"
                    )
                ]
            )
        )

    def create_bedrock_agent_and_kb(self):
        """Bedrock Agent 및 Knowledge Base 생성"""
        
        # 1. Knowledge Base용 S3 버킷 (이미 있는 버킷 사용)
        # self.prompt_bucket 사용
        
        # 2. Knowledge Base용 OpenSearch 인덱스 (임시로 간단한 구조)
        # OpenSearch가 비활성화되어 있으므로 Vector Store 없이 구성
        
        # 3. Bedrock Agent IAM 역할
        self.agent_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Bedrock Agent execution role"
        )
        
        # Agent에 필요한 권한 추가
        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
                ]
            )
        )
        
        # S3 버킷 접근 권한
        self.agent_role.add_to_policy(
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
        
        # Knowledge Base IAM 역할
        self.kb_role = iam.Role(
            self, "BedrockKnowledgeBaseRole", 
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Knowledge Base execution role"
        )
        
        # Knowledge Base에 필요한 권한
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v1"
                ]
            )
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
        
        # 4. 임시로 Knowledge Base 없이 Agent만 생성
        # 추후 OpenSearch 설정 후 Knowledge Base 추가 예정
        
        # 5. Bedrock Agent 생성 (Knowledge Base 없이)
        self.bedrock_agent = bedrock.CfnAgent(
            self, "TitleNomicsAgent",
            agent_name="title-nomics-agent",
            description="서울경제신문 제목 생성 AI 어시스턴트",
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
            agent_resource_role_arn=self.agent_role.role_arn,
            idle_session_ttl_in_seconds=1800,  # 30분
            instruction="""당신은 서울경제신문의 TITLE-NOMICS AI 어시스턴트입니다.

주요 역할:
1. 뉴스 기사의 제목을 생성하고 개선하는 것
2. 편집부의 스타일 가이드를 준수하는 것
3. 독자의 관심을 끌고 클릭률을 높이는 제목을 만드는 것

기본 원칙:
- 정확하고 객관적인 정보 전달
- 서울경제신문의 브랜드 톤앤매너 유지
- 독자층에 맞는 적절한 표현 사용
- SEO 최적화를 고려한 키워드 활용

프로젝트별 커스터마이징 정보는 대화 중에 제공될 예정입니다.""",
            guardrail_configuration=bedrock.CfnAgent.GuardrailConfigurationProperty(
                guardrail_identifier=self.guardrail.attr_guardrail_id,
                guardrail_version="DRAFT"
            )
        )
        
        # 6. Agent Alias 생성 (배포용)
        self.agent_alias = bedrock.CfnAgentAlias(
            self, "TitleNomicsAgentAlias",
            agent_alias_name="production",
            agent_id=self.bedrock_agent.attr_agent_id,
            description="Production alias for Title-Nomics agent"
        )

    def create_lambda_functions(self):
        """Lambda 함수들 생성 - 정리된 버전"""
        # 공통 IAM 역할
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )

        # Step Functions 실행 권한 추가
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSStepFunctionsFullAccess")
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
                    "sns:Publish"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn + "/*",
                    self.article_bucket.bucket_arn + "/*",
                    self.project_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_meta_table.table_arn + "/index/projectId-stepOrder-index",
                    self.conversation_table.table_arn,
                    self.execution_table.table_arn,
                    self.chat_history_table.table_arn,
                    self.chat_session_table.table_arn,
                    self.dlq.queue_arn,
                    self.index_queue.queue_arn,
                    self.completion_topic.topic_arn,
                    self.error_topic.topic_arn
                ]
            )
        )

        # LangChain Lambda Layer 생성
        langchain_layer = lambda_.LayerVersion(
            self, "LangChainLayer",
            layer_version_name="langchain-dependencies",
            code=lambda_.Code.from_asset("../lambda_layers/langchain-layer.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="LangChain and related dependencies for Bedrock integration",
            removal_policy=RemovalPolicy.DESTROY
        )

        # 1. 제목 생성 Lambda (메인 기능)
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            function_name="bedrock-diy-generate-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.handler",
            code=lambda_.Code.from_asset("../lambda/generate"),
            role=lambda_role,
            timeout=Duration.minutes(3),
            memory_size=1024,
            environment={
                "STATE_MACHINE_ARN": "",
                "EXECUTION_TABLE": self.execution_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "REGION": self.region
            }
        )

        # 2. 채팅 라우터 Lambda (LangChain 기반 프롬프트 체이닝)
        self.langchain_router_lambda = lambda_.Function(
            self, "LangChainRouterFunction",
            function_name="bedrock-diy-langchain-router-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="langchain_router.handler",
            code=lambda_.Code.from_asset("../lambda/langchain_router"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            memory_size=2048,
            layers=[langchain_layer],
            environment={
                "CHAT_HISTORY_TABLE": self.chat_history_table.table_name,
                "CHAT_SESSION_TABLE": self.chat_session_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "BEDROCK_SUMMARY_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0"
            }
        )

        # 3. 프로젝트 관리 Lambda
        self.project_lambda = lambda_.Function(
            self, "ProjectFunction",
            function_name="bedrock-diy-project-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="project.handler",
            code=lambda_.Code.from_asset("../lambda/project"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "PROJECT_TABLE": self.project_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region
            }
        )

        # 4. 인증 Lambda
        self.auth_lambda = lambda_.Function(
            self, "AuthFunction",
            function_name="bedrock-diy-auth-main",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="auth.handler",
            code=lambda_.Code.from_asset("../lambda/auth"),
            role=lambda_role,
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "REGION": self.region
            }
        )

        # 5. 프롬프트 저장 Lambda (임베딩 포함)
        self.save_prompt_lambda = lambda_.Function(
            self, "SavePromptFunction",
            function_name="bedrock-diy-save-prompt-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="save_prompt.handler",
            code=lambda_.Code.from_asset("../lambda/save_prompt"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region
            }
        )

        # Step Functions 관련 Lambda들 (조건부 생성)
        self.create_step_functions_lambdas(lambda_role)

    def create_step_functions_lambdas(self, lambda_role):
        """Step Functions 관련 Lambda 함수들 생성"""
        
        # 1. 프롬프트 조회 Lambda
        self.fetch_prompts_lambda = lambda_.Function(
            self, "FetchPromptsFunction",
            function_name="bedrock-diy-fetch-prompts-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="fetch_prompts.handler",
            code=lambda_.Code.from_asset("../lambda/fetch_prompts"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region
            }
        )

        # 2. 페이로드 준비 Lambda
        self.build_payload_lambda = lambda_.Function(
            self, "BuildPayloadFunction",
            function_name="bedrock-diy-build-payload-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="build_payload.handler",
            code=lambda_.Code.from_asset("../lambda/build_payload"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "REGION": self.region
            }
        )

        # 3. 결과 저장 Lambda
        self.save_results_lambda = lambda_.Function(
            self, "SaveResultsFunction",
            function_name="bedrock-diy-save-results-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="save_results.handler",
            code=lambda_.Code.from_asset("../lambda/save_results"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "CONVERSATION_TABLE": self.conversation_table.table_name,
                "ARTICLE_BUCKET": self.article_bucket.bucket_name,
                "COMPLETION_TOPIC": self.completion_topic.topic_arn,
                "REGION": self.region
            }
        )

        # 4. 에러 처리 Lambda
        self.error_handler_lambda = lambda_.Function(
            self, "ErrorHandlerFunction",
            function_name="bedrock-diy-error-handler-auth",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="error_handler.handler",
            code=lambda_.Code.from_asset("../lambda/error_handler"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=256,
            environment={
                "EXECUTION_TABLE": self.execution_table.table_name,
                "ERROR_TOPIC": self.error_topic.topic_arn,
                "REGION": self.region
            }
        )

    def create_api_gateway(self):
        """API Gateway 생성 - 정리된 버전"""
        # REST API 생성
        self.api = apigateway.RestApi(
            self, "BedrockDiyApi",
            rest_api_name="bedrock-diy-api",
            description="TITLE-NOMICS API - 서울경제신문 AI 제목 생성 시스템",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["*", "Authorization"]
            )
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
        
        # 채팅 관련 경로 생성
        self.create_chat_routes()
        
        # 프롬프트 관리 경로 생성
        self.create_prompt_routes()

    def create_auth_routes(self):
        """인증 관련 API 경로 생성"""
        auth_resource = self.api.root.add_resource("auth")
        
        # 인증 엔드포인트들 (Authorization 불필요)
        auth_endpoints = ["signup", "signin", "refresh", "signout", "verify", "forgot-password", "confirm-password"]
        
        for endpoint in auth_endpoints:
            auth_resource.add_resource(endpoint).add_method(
                "POST",
                apigateway.LambdaIntegration(self.auth_lambda),
                authorization_type=apigateway.AuthorizationType.NONE
            )

    def create_project_routes(self):
        """프로젝트 관련 API 경로 생성"""
        projects_resource = self.api.root.add_resource("projects")
        
        # POST /projects (프로젝트 생성)
        projects_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # GET /projects (프로젝트 목록)
        projects_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # /projects/{id} 리소스
        project_resource = projects_resource.add_resource("{projectId}")
        
        # GET /projects/{id} (프로젝트 상세)
        project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # POST /projects/{id}/generate (제목 생성)
        generate_resource = project_resource.add_resource("generate")
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # GET /projects/{id}/upload-url (파일 업로드용 pre-signed URL)
        upload_url_resource = project_resource.add_resource("upload-url")
        upload_url_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

    def create_chat_routes(self):
        """채팅 관련 API 경로 생성"""
        projects_resource = self.api.root.get_resource("projects")
        project_resource = projects_resource.get_resource("{projectId}")
        
        # POST /projects/{id}/chat (LangChain 채팅 - 프롬프트 체이닝)
        chat_resource = project_resource.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # GET /projects/{id}/chat/sessions (채팅 세션 목록)
        chat_sessions_resource = chat_resource.add_resource("sessions")
        chat_sessions_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # GET /projects/{id}/chat/sessions/{sessionId} (채팅 히스토리)
        chat_session_resource = chat_sessions_resource.add_resource("{sessionId}")
        chat_session_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

        # DELETE /projects/{id}/chat/sessions/{sessionId} (채팅 세션 삭제)
        chat_session_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

    def create_prompt_routes(self):
        """프롬프트 관리 API 경로 생성"""
        prompts_resource = self.api.root.add_resource("prompts")
        prompts_project_resource = prompts_resource.add_resource("{projectId}")
        
        # POST /prompts/{projectId} (새 프롬프트 카드 생성)
        prompts_project_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )
        
        # GET /prompts/{projectId} (프롬프트 카드 목록 조회)
        prompts_project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )
        
        # /prompts/{projectId}/{promptId} 리소스
        prompt_card_resource = prompts_project_resource.add_resource("{promptId}")
        
        # PUT /prompts/{projectId}/{promptId} (프롬프트 카드 수정)
        prompt_card_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.save_prompt_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )
        
        # DELETE /prompts/{projectId}/{promptId} (프롬프트 카드 삭제)
        prompt_card_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.save_prompt_lambda),
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorizer=self.api_authorizer
        )

    def create_step_functions(self):
        """Step Functions 스테이트 머신 생성"""
        # Step Functions 실행 역할
        sf_role = iam.Role(
            self, "StepFunctionsRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AWSStepFunctionsFullAccess")
            ]
        )

        # Bedrock 및 Lambda 호출 권한 추가
        sf_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:ApplyGuardrail", 
                    "lambda:InvokeFunction",
                    "sns:Publish"
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}:{self.account}:*",
                    self.fetch_prompts_lambda.function_arn,
                    self.build_payload_lambda.function_arn,
                    self.save_results_lambda.function_arn,
                    self.error_handler_lambda.function_arn,
                    self.completion_topic.topic_arn,
                    self.error_topic.topic_arn,
                    self.guardrail.attr_guardrail_arn
                ]
            )
        )

        # workflow.yaml 파일 읽기
        with open('workflow.yaml', 'r') as f:
            workflow_definition = f.read()

        # Step Functions 스테이트 머신 생성
        self.state_machine = stepfunctions.CfnStateMachine(
            self, "TitleGenerationStateMachine",
            state_machine_name="bedrock-diy-title-generation",
            definition_string=workflow_definition,
            role_arn=sf_role.role_arn,
            logging_configuration=stepfunctions.CfnStateMachine.LoggingConfigurationProperty(
                level="ALL",
                include_execution_data=True,
                destinations=[
                    stepfunctions.CfnStateMachine.LogDestinationProperty(
                        cloud_watch_logs_log_group=stepfunctions.CfnStateMachine.CloudWatchLogsLogGroupProperty(
                            log_group_arn=f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/stepfunctions/bedrock-diy-title-generation"
                        )
                    )
                ]
            ),
            definition_substitutions={
                "FetchPromptsFn": self.fetch_prompts_lambda.function_name,
                "BuildPayloadFn": self.build_payload_lambda.function_name,
                "SaveResultsFn": self.save_results_lambda.function_name,
                "ErrorHandlerFn": self.error_handler_lambda.function_name,
                "ProjectGuardrail": self.guardrail.attr_guardrail_id,
                "CompletionTopic": self.completion_topic.topic_arn
            }
        )

        # Generate Lambda에 State Machine ARN 업데이트
        self.generate_lambda.add_environment("STATE_MACHINE_ARN", self.state_machine.attr_arn)

    def create_cloudwatch_alarms(self):
        """CloudWatch 알람 생성"""
        # Lambda 함수 오류율 알람
        lambda_funcs = [
            (self.generate_lambda, "Generate"),
            (self.project_lambda, "Project"),
            (self.langchain_router_lambda, "LangChainRouter"),
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
        """비용 알람 생성"""
        # 월 $1000 예산 알람
        budgets.CfnBudget(
            self, "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name="bedrock-diy-monthly-budget",
                budget_type="COST",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=1000,
                    unit="USD"
                ),
                time_unit="MONTHLY",
                cost_filters={
                    "Service": ["Amazon Bedrock", "AWS Lambda", "Amazon OpenSearch Service"]
                }
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL",
                            address="admin@example.com"  # 실제 이메일로 변경
                        )
                    ]
                )
            ]
        )

    def create_outputs(self):
        """CDK 출력값 생성"""
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name="ApiGatewayUrl"
        )
        
        # API Gateway 도메인만 별도로 export (CloudFront에서 사용)
        api_domain = self.api.url.replace("https://", "").replace("http://", "")
        if api_domain.endswith("/"):
            api_domain = api_domain[:-1]
        
        CfnOutput(
            self, "ApiGatewayDomain",
            value=api_domain,
            description="API Gateway Domain for CloudFront",
            export_name="ApiGatewayDomain"
        )
        
        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름",
            export_name="PromptBucketName"
        )
        
        CfnOutput(
            self, "BedrockAgentId",
            value=self.bedrock_agent.attr_agent_id,
            description="Bedrock Agent ID",
            export_name="BedrockAgentId"
        )
        
        CfnOutput(
            self, "BedrockAgentAliasId",
            value=self.agent_alias.attr_agent_alias_id,
            description="Bedrock Agent Alias ID",
            export_name="BedrockAgentAliasId"
        )
        
        # CfnOutput(
        #     self, "OpenSearchEndpoint",
        #     value=self.opensearch_domain.domain_endpoint,
        #     description="OpenSearch 도메인 엔드포인트"
        # )
        
        # CfnOutput(
        #     self, "StateMachineArn",
        #     value=self.state_machine.attr_arn,
        #     description="Step Functions 스테이트 머신 ARN"
        # )
        
        CfnOutput(
            self, "GuardrailId",
            value=self.guardrail.attr_guardrail_id,
            description="Bedrock Guardrail ID",
            export_name="GuardrailId"
        )
        
        # Cognito 출력값 추가
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito 사용자 풀 ID",
            export_name="UserPoolId"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito 사용자 풀 클라이언트 ID",
            export_name="UserPoolClientId"
        )
        
        CfnOutput(
            self, "CognitoDomainUrl",
            value=f"https://{self.user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
            description="Cognito 도메인 URL (Hosted UI)",
            export_name="CognitoDomainUrl"
        ) 