from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_opensearch as opensearch,
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
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct
import json

class BedrockDiyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. S3 버킷들 생성
        self.create_s3_buckets()
        
        # 2. DynamoDB 테이블들 생성
        self.create_dynamodb_tables()
        
        # 3. OpenSearch 도메인 생성
        self.create_opensearch_domain()
        
        # 4. SQS DLQ 생성
        self.create_sqs_dlq()
        
        # 5. SNS 토픽 생성
        self.create_sns_topics()
        
        # 6. Bedrock Guardrail 생성
        self.create_bedrock_guardrail()
        
        # 7. Lambda 함수들 생성
        self.create_lambda_functions()
        
        # 8. Step Functions 생성
        self.create_step_functions()
        
        # 9. API Gateway 생성
        self.create_api_gateway()
        
        # 10. S3 이벤트 트리거 설정
        self.setup_s3_triggers()
        
        # 11. CloudWatch 알람 설정 (강화)
        self.create_cloudwatch_alarms()
        
        # 12. 비용 알람 설정
        self.create_budget_alarms()
        
        # 13. CDK 출력값 생성
        self.create_outputs()

    def create_s3_buckets(self):
        """S3 버킷 생성"""
        # 프롬프트 파일 저장용 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"bedrock-diy-prompts-{self.account}-{self.region}",
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
            bucket_name=f"bedrock-diy-articles-{self.account}-{self.region}",
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
            table_name="bedrock-diy-projects",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=True
        )

        # 프롬프트 메타데이터 테이블
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name="bedrock-diy-prompt-meta",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="promptKey",  # category#fileName
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 대화/생성 기록 테이블
        self.conversation_table = dynamodb.Table(
            self, "ConversationTable",
            table_name="bedrock-diy-conversations",
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
            table_name="bedrock-diy-executions",
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
            table_name="bedrock-diy-chat-history",
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
            table_name="bedrock-diy-chat-sessions",
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
                volume_type=opensearch.EbsVolumeType.GP3
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
            queue_name="bedrock-diy-index-prompt-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # 메인 큐 (S3 이벤트 재시도용)
        self.index_queue = sqs.Queue(
            self, "IndexPromptQueue", 
            queue_name="bedrock-diy-index-prompt",
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
            topic_name="bedrock-diy-completion"
        )

        self.error_topic = sns.Topic(
            self, "ErrorTopic", 
            topic_name="bedrock-diy-errors"
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

    def create_lambda_functions(self):
        """Lambda 함수들 생성"""
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

        # S3, DynamoDB, OpenSearch 권한 추가
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "dynamodb:Query",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:GetItem",
                    "dynamodb:Scan",
                    "es:ESHttpPost",
                    "es:ESHttpPut",
                    "es:ESHttpGet",
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sns:Publish"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn + "/*",
                    self.article_bucket.bucket_arn + "/*",
                    self.project_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.conversation_table.table_arn,
                    self.execution_table.table_arn,
                    self.chat_history_table.table_arn,
                    self.chat_session_table.table_arn,
                    self.opensearch_domain.domain_arn + "/*",
                    self.dlq.queue_arn,
                    self.index_queue.queue_arn,
                    self.completion_topic.topic_arn,
                    self.error_topic.topic_arn
                ]
            )
        )

        # 1. 프롬프트 색인 Lambda (기존)
        self.index_prompt_lambda = lambda_.Function(
            self, "IndexPromptFunction",
            function_name="bedrock-diy-index-prompt",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index_prompt.handler",
            code=lambda_.Code.from_asset("lambda/index_prompt"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "REGION": self.region,
                "DLQ_URL": self.dlq.queue_url
            }
        )

        # 2. 프롬프트 조회 Lambda (Step Functions용)
        self.fetch_prompts_lambda = lambda_.Function(
            self, "FetchPromptsFunction",
            function_name="bedrock-diy-fetch-prompts",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="fetch_prompts.handler",
            code=lambda_.Code.from_asset("lambda/fetch_prompts"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=1024,
            environment={
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "REGION": self.region
            }
        )

        # 3. 페이로드 준비 Lambda (Step Functions용)
        self.build_payload_lambda = lambda_.Function(
            self, "BuildPayloadFunction",
            function_name="bedrock-diy-build-payload",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="build_payload.handler",
            code=lambda_.Code.from_asset("lambda/build_payload"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=1024,
            environment={
                "REGION": self.region
            }
        )

        # 4. 결과 저장 Lambda (Step Functions용)
        self.save_results_lambda = lambda_.Function(
            self, "SaveResultsFunction",
            function_name="bedrock-diy-save-results",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="save_results.handler",
            code=lambda_.Code.from_asset("lambda/save_results"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "CONVERSATION_TABLE": self.conversation_table.table_name,
                "EXECUTION_TABLE": self.execution_table.table_name,
                "REGION": self.region
            }
        )

        # 5. 오류 처리 Lambda (Step Functions용)
        self.error_handler_lambda = lambda_.Function(
            self, "ErrorHandlerFunction",
            function_name="bedrock-diy-error-handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="error_handler.handler",
            code=lambda_.Code.from_asset("lambda/error_handler"),
            role=lambda_role,
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "EXECUTION_TABLE": self.execution_table.table_name,
                "ERROR_TOPIC": self.error_topic.topic_arn,
                "REGION": self.region
            }
        )

        # 6. 제목 생성 Lambda (Step Functions 트리거용)
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            function_name="bedrock-diy-generate",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.handler",
            code=lambda_.Code.from_asset("lambda/generate"),
            role=lambda_role,
            timeout=Duration.minutes(1),
            memory_size=512,
            environment={
                "STATE_MACHINE_ARN": "", # Step Functions 생성 후 업데이트
                "EXECUTION_TABLE": self.execution_table.table_name,
                "REGION": self.region
            }
        )

        # 🆕 7. LangChain 채팅 라우터 Lambda
        self.langchain_router_lambda = lambda_.Function(
            self, "LangChainRouterFunction",
            function_name="bedrock-diy-langchain-router",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="langchain_router.handler",
            code=lambda_.Code.from_asset("lambda/langchain_router"),
            role=lambda_role,
            timeout=Duration.minutes(5),
            memory_size=2048,  # LangChain은 메모리를 많이 씀
            layers=[
                # LangChain Layer 추가 예정
            ],
            environment={
                "CHAT_HISTORY_TABLE": self.chat_history_table.table_name,
                "CHAT_SESSION_TABLE": self.chat_session_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "OPENSEARCH_ENDPOINT": self.opensearch_domain.domain_endpoint,
                "REGION": self.region,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "BEDROCK_SUMMARY_MODEL_ID": "amazon.titan-text-lite-v1"
            }
        )

        # 8. 프로젝트 관리 Lambda (기존)
        self.project_lambda = lambda_.Function(
            self, "ProjectFunction",
            function_name="bedrock-diy-project",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="project.handler",
            code=lambda_.Code.from_asset("lambda/project"),
            role=lambda_role,
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "PROJECT_TABLE": self.project_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region
            }
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

    def create_api_gateway(self):
        """API Gateway 생성"""
        # REST API 생성
        self.api = apigateway.RestApi(
            self, "BedrockDiyApi",
            rest_api_name="bedrock-diy-api",
            description="AWS Bedrock DIY Claude 프로젝트 API",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["*"]
            )
        )

        # /projects 리소스
        projects_resource = self.api.root.add_resource("projects")
        
        # POST /projects (프로젝트 생성)
        projects_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # GET /projects (프로젝트 목록)
        projects_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # /projects/{id} 리소스
        project_resource = projects_resource.add_resource("{projectId}")
        
        # GET /projects/{id} (프로젝트 상세)
        project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # POST /projects/{id}/generate (Step Functions 실행)
        generate_resource = project_resource.add_resource("generate")
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # 🆕 POST /projects/{id}/chat (LangChain 채팅)
        chat_resource = project_resource.add_resource("chat")
        chat_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # 🆕 GET /projects/{id}/chat/sessions (채팅 세션 목록)
        chat_sessions_resource = chat_resource.add_resource("sessions")
        chat_sessions_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # 🆕 GET /projects/{id}/chat/sessions/{sessionId} (채팅 히스토리)
        chat_session_resource = chat_sessions_resource.add_resource("{sessionId}")
        chat_session_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # 🆕 DELETE /projects/{id}/chat/sessions/{sessionId} (채팅 세션 삭제)
        chat_session_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.langchain_router_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # /presign-url 리소스
        presign_resource = self.api.root.add_resource("presign-url")
        presign_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # /executions 리소스 (실행 상태 조회)
        executions_resource = self.api.root.add_resource("executions")
        execution_resource = executions_resource.add_resource("{executionArn}")
        execution_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.generate_lambda),
            authorization_type=apigateway.AuthorizationType.NONE
        )

    def setup_s3_triggers(self):
        """S3 이벤트 트리거 설정"""
        # 프롬프트 버킷에 파일 업로드 시 색인 Lambda 트리거
        self.prompt_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(self.index_prompt_lambda)
        )

    def create_cloudwatch_alarms(self):
        """CloudWatch 알람 생성 (강화)"""
        # Lambda 함수 오류율 알람
        for lambda_func in [self.index_prompt_lambda, self.generate_lambda, self.project_lambda, 
                           self.fetch_prompts_lambda, self.build_payload_lambda, self.save_results_lambda]:
            cloudwatch.Alarm(
                self, f"{lambda_func.function_name}ErrorAlarm",
                metric=lambda_func.metric_errors(period=Duration.minutes(5)),
                threshold=3,
                evaluation_periods=2,
                alarm_description=f"{lambda_func.function_name} 함수 오류율이 높습니다"
            )

        # Step Functions 실행 실패 알람
        cloudwatch.Alarm(
            self, "StepFunctionsFailureAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsFailed",
                dimensions={
                    "StateMachineArn": self.state_machine.attr_arn
                }
            ),
            threshold=3,
            evaluation_periods=2,
            alarm_description="Step Functions 실행 실패가 증가하고 있습니다"
        )

        # OpenSearch 메모리 사용률 알람
        cloudwatch.Alarm(
            self, "OpenSearchMemoryAlarm",
            metric=cloudwatch.Metric(
                namespace="AWS/ES",
                metric_name="JVMMemoryPressure",
                dimensions={
                    "DomainName": self.opensearch_domain.domain_name,
                    "ClientId": self.account
                }
            ),
            threshold=80,
            evaluation_periods=2,
            alarm_description="OpenSearch 메모리 사용률이 80%를 초과했습니다"
        )

        # DLQ 메시지 알람
        cloudwatch.Alarm(
            self, "DLQMessageAlarm",
            metric=self.dlq.metric_approximate_number_of_visible_messages(),
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
            description="API Gateway URL"
        )
        
        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름"
        )
        
        CfnOutput(
            self, "OpenSearchEndpoint",
            value=self.opensearch_domain.domain_endpoint,
            description="OpenSearch 도메인 엔드포인트"
        )
        
        CfnOutput(
            self, "StateMachineArn",
            value=self.state_machine.attr_arn,
            description="Step Functions 스테이트 머신 ARN"
        )
        
        CfnOutput(
            self, "GuardrailId",
            value=self.guardrail.attr_guardrail_id,
            description="Bedrock Guardrail ID"
        ) 