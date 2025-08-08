"""
개선된 Bedrock Stack - AWS 리소스 충돌 방지 버전
이 파일은 bedrock_stack.py의 개선된 버전입니다.
"""
import time
import hashlib
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_cognito as cognito,
    RemovalPolicy,
    Duration,
    CfnOutput,
    Tags
)
from constructs import Construct

class ImprovedBedrockStack(Stack):
    
    def __init__(self, scope: Construct, construct_id: str, 
                 project_name: str,
                 project_prefix: str,
                 project_id: str = None,
                 environment_name: str = "dev",
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 프로젝트 설정
        self.project_name = project_name
        self.project_prefix = project_prefix
        self.environment_name = environment_name
        
        # 프로젝트 고유 ID 생성 (충돌 방지용)
        if project_id:
            self.project_id = project_id
        else:
            # 프로젝트 이름과 계정 ID를 기반으로 8자 고유 ID 생성
            unique_string = f"{project_name}-{self.account}"
            self.project_id = hashlib.md5(unique_string.encode()).hexdigest()[:8]
        
        # 리소스 네이밍 컨벤션
        self.resource_prefix = f"{self.project_prefix}-{self.project_id}"
        
        # 태그 추가
        Tags.of(self).add("Project", self.project_name)
        Tags.of(self).add("ProjectID", self.project_id)
        Tags.of(self).add("Environment", self.environment_name)
        Tags.of(self).add("ManagedBy", "CDK")
        
        # 리소스 생성
        self.create_cognito_user_pool()
        self.create_s3_buckets()
        self.create_dynamodb_tables()
        self.create_lambda_functions()
        self.create_api_gateway()
        self.create_websocket_api()
    
    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성 - 고유 이름 사용"""
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"{self.resource_prefix}-users-{self.environment_name}",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            removal_policy=RemovalPolicy.DESTROY
        )
        
        self.user_pool_client = self.user_pool.add_client(
            "WebClient",
            user_pool_client_name=f"{self.resource_prefix}-web-client-{self.environment_name}",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False
        )
    
    def create_s3_buckets(self):
        """S3 버킷 생성 - 계정과 리전 포함으로 충돌 방지"""
        # 프롬프트 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"{self.resource_prefix}-prompts-{self.environment_name}-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # 아티클 버킷
        self.article_bucket = s3.Bucket(
            self, "ArticleBucket",
            bucket_name=f"{self.resource_prefix}-articles-{self.environment_name}-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
    
    def create_dynamodb_tables(self):
        """DynamoDB 테이블 생성 - 프로젝트 ID 포함"""
        # 프롬프트 메타 테이블
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name=f"{self.resource_prefix}-prompt-meta-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="prompt_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 사용자 테이블
        self.users_table = dynamodb.Table(
            self, "UsersTable", 
            table_name=f"{self.resource_prefix}-users-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 대화 테이블
        self.conversations_table = dynamodb.Table(
            self, "ConversationsTable",
            table_name=f"{self.resource_prefix}-conversations-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # 메시지 테이블
        self.messages_table = dynamodb.Table(
            self, "MessagesTable",
            table_name=f"{self.resource_prefix}-messages-{self.environment_name}",
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
        
        # WebSocket 연결 테이블
        self.websocket_connections_table = dynamodb.Table(
            self, "WebSocketConnectionsTable",
            table_name=f"{self.resource_prefix}-ws-connections-{self.environment_name}",
            partition_key=dynamodb.Attribute(
                name="connection_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
    
    def create_lambda_functions(self):
        """Lambda 함수 생성 - 명시적 이름 지정"""
        # Lambda 실행 역할 (공통)
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            role_name=f"{self.resource_prefix}-lambda-role-{self.environment_name}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        
        # Bedrock 정책 추가
        lambda_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))
        
        # Generate Lambda
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            function_name=f"{self.resource_prefix}-generate-{self.environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="generate.lambda_handler",
            code=lambda_.Code.from_asset("../backend"),
            timeout=Duration.seconds(300),
            memory_size=1024,
            role=lambda_role,
            environment={
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "PROJECT_NAME": self.project_name,
                "ENVIRONMENT": self.environment_name
            }
        )
        
        # Auth Lambda  
        self.auth_lambda = lambda_.Function(
            self, "AuthFunction",
            function_name=f"{self.resource_prefix}-auth-{self.environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="auth.lambda_handler",
            code=lambda_.Code.from_asset("../backend"),
            timeout=Duration.seconds(30),
            memory_size=256,
            role=lambda_role,
            environment={
                "USERS_TABLE": self.users_table.table_name,
                "USER_POOL_ID": self.user_pool.user_pool_id
            }
        )
        
        # 권한 부여
        self.prompt_bucket.grant_read_write(self.generate_lambda)
        self.users_table.grant_read_write_data(self.auth_lambda)
    
    def create_api_gateway(self):
        """API Gateway 생성 - 고유 이름 사용"""
        # REST API
        self.api = apigateway.RestApi(
            self, "RestApi",
            rest_api_name=f"{self.resource_prefix}-api-{self.environment_name}",
            description=f"{self.project_name} REST API ({self.environment_name})",
            deploy_options=apigateway.StageOptions(
                stage_name=self.environment_name,
                throttling_rate_limit=100,
                throttling_burst_limit=200
            )
        )
        
        # API 리소스 추가
        generate = self.api.root.add_resource("generate")
        generate.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda)
        )
    
    def create_websocket_api(self):
        """WebSocket API 생성 - 고유 이름 사용"""
        # WebSocket Lambda 함수들
        self.ws_connect_lambda = lambda_.Function(
            self, "WsConnectFunction",
            function_name=f"{self.resource_prefix}-ws-connect-{self.environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="connect.lambda_handler",
            code=lambda_.Code.from_asset("../backend/websocket"),
            timeout=Duration.seconds(30),
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name
            }
        )
        
        self.ws_disconnect_lambda = lambda_.Function(
            self, "WsDisconnectFunction", 
            function_name=f"{self.resource_prefix}-ws-disconnect-{self.environment_name}",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="disconnect.lambda_handler",
            code=lambda_.Code.from_asset("../backend/websocket"),
            timeout=Duration.seconds(30),
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name
            }
        )
        
        # WebSocket API
        self.websocket_api = apigatewayv2.WebSocketApi(
            self, "WebSocketApi",
            api_name=f"{self.resource_prefix}-websocket-{self.environment_name}",
            description=f"{self.project_name} WebSocket API ({self.environment_name})",
            connect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    self.ws_connect_lambda
                )
            ),
            disconnect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration", 
                    self.ws_disconnect_lambda
                )
            )
        )
        
        # WebSocket Stage
        self.websocket_stage = apigatewayv2.WebSocketStage(
            self, "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name=self.environment_name,
            auto_deploy=True
        )
        
        # 권한 부여
        self.websocket_connections_table.grant_read_write_data(self.ws_connect_lambda)
        self.websocket_connections_table.grant_read_write_data(self.ws_disconnect_lambda)
    
    def add_outputs(self):
        """스택 출력값 추가"""
        CfnOutput(
            self, "ProjectInfo",
            value=f"Project: {self.project_name} (ID: {self.project_id})",
            description="Project Information"
        )
        
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="REST API Gateway URL"
        )
        
        CfnOutput(
            self, "WebSocketApiUrl",
            value=self.websocket_stage.url,
            description="WebSocket API URL"
        )
        
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID"
        )