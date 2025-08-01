from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_iam as iam,
    RemovalPolicy
)
from constructs import Construct

class ConversationStack(Stack):
    """
    CDK Stack for Conversation History functionality
    - DynamoDB tables for Conversations and Messages
    - Lambda functions for conversation APIs
    - API Gateway endpoints
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 환경 이름 설정 (DynamoDB 테이블 이름에 사용)
        if "Dev" in construct_id:
            self.env_suffix = "dev"
        else:
            self.env_suffix = "prod"

        # DynamoDB Tables
        self.conversations_table = self._create_conversations_table()
        self.messages_table = self._create_messages_table()
        
        # Prompt-related Tables
        self.admin_prompt_cards_table = self._create_admin_prompt_cards_table()
        self.global_prompt_library_table = self._create_global_prompt_library_table()
        self.prompt_evaluations_table = self._create_prompt_evaluations_table()
        self.agent_thoughts_table = self._create_agent_thoughts_table()
        self.step_configurations_table = self._create_step_configurations_table()
        
        # Lambda Functions
        self.conversation_lambda = self._create_conversation_lambda()
        self.message_lambda = self._create_message_lambda()
        
        # Prompt-related Lambda Functions
        self.prompt_evaluation_lambda = self._create_prompt_evaluation_lambda()
        self.save_prompt_lambda = self._create_save_prompt_lambda()
        
        # API Gateway endpoints will be added to existing API
        
    def _create_conversations_table(self) -> dynamodb.Table:
        """Create Conversations table with GSI for user queries"""
        table = dynamodb.Table(
            self, "ConversationsTable",
            table_name=f"nexus-title-generator-conversations-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # USER#<cognito_sub>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # CONV#<uuid>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            time_to_live_attribute="ttl"
        )
        
        # GSI for querying conversations by lastActivityAt
        table.add_global_secondary_index(
            index_name="GSI1-LastActivity",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",  # USER#<cognito_sub>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="lastActivityAt",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table
    
    def _create_messages_table(self) -> dynamodb.Table:
        """Create Messages table for storing conversation messages"""
        table = dynamodb.Table(
            self, "MessagesTable", 
            table_name=f"nexus-title-generator-messages-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # CONV#<uuid>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # TS#<iso_timestamp>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True,
            time_to_live_attribute="ttl"
        )
        
        return table
    
    def _create_admin_prompt_cards_table(self) -> dynamodb.Table:
        """Create AdminPromptCards table for admin-only prompt cards with versioning"""
        table = dynamodb.Table(
            self, "AdminPromptCardsTable",
            table_name=f"nexus-title-generator-admin-prompt-cards-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # ADMIN#<admin_id>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # CARD#<card_id>#<version>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery=True
        )
        
        # GSI for querying cards by status
        table.add_global_secondary_index(
            index_name="GSI1-CardStatus",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",  # ADMIN#<admin_id>#STATUS#<status>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="updatedAt",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table
    
    def _create_prompt_evaluations_table(self) -> dynamodb.Table:
        """Create PromptEvaluations table for step-by-step evaluation results"""
        table = dynamodb.Table(
            self, "PromptEvaluationsTable",
            table_name=f"nexus-title-generator-prompt-evaluations-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # CARD#<card_id>#<version>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # STEP#<step_number>#EVAL#<timestamp>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        return table
    
    def _create_agent_thoughts_table(self) -> dynamodb.Table:
        """Create AgentThoughts table for real-time agent thinking process"""
        table = dynamodb.Table(
            self, "AgentThoughtsTable",
            table_name=f"nexus-title-generator-agent-thoughts-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # SESSION#<evaluation_session_id>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # THOUGHT#<timestamp>#<sequence>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            time_to_live_attribute="ttl"  # Auto-delete after 30 days
        )
        
        return table
    
    def _create_step_configurations_table(self) -> dynamodb.Table:
        """Create StepConfigurations table for evaluation step settings"""
        table = dynamodb.Table(
            self, "StepConfigurationsTable",
            table_name=f"nexus-title-generator-step-configurations-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # CONFIG#STEPS
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # STEP#<step_number>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        return table
    
    def _create_global_prompt_library_table(self) -> dynamodb.Table:
        """Create GlobalPromptLibrary table for approved prompts available to all users"""
        table = dynamodb.Table(
            self, "GlobalPromptLibraryTable", 
            table_name=f"nexus-title-generator-global-prompt-library-{self.env_suffix}",
            partition_key=dynamodb.Attribute(
                name="PK",  # GLOBAL#PROMPTS
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # CARD#<card_id>#<approved_timestamp>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN
        )
        
        # GSI for querying by category
        table.add_global_secondary_index(
            index_name="GSI1-Category",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",  # CATEGORY#<category>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="approvedAt",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table
    
    def _create_conversation_lambda(self) -> _lambda.Function:
        """Lambda for conversation management (GET /conversations, POST /conversation)"""
        lambda_function = _lambda.Function(
            self, "ConversationFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/conversation"),
            handler="conversation_api.handler",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "CONVERSATIONS_TABLE": self.conversations_table.table_name,
                "MESSAGES_TABLE": self.messages_table.table_name
            }
        )
        
        # Grant permissions to DynamoDB tables
        self.conversations_table.grant_read_write_data(lambda_function)
        self.messages_table.grant_read_write_data(lambda_function)  # 메시지 삭제를 위해 write 권한 필요
        
        return lambda_function
    
    def _create_message_lambda(self) -> _lambda.Function:
        """Lambda for message management (GET /messages)"""
        lambda_function = _lambda.Function(
            self, "MessageFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/message"),
            handler="message_api.handler", 
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "MESSAGES_TABLE": self.messages_table.table_name,
                "CONVERSATIONS_TABLE": self.conversations_table.table_name
            }
        )
        
        # Grant permissions to DynamoDB tables
        self.messages_table.grant_read_write_data(lambda_function)
        self.conversations_table.grant_read_write_data(lambda_function)
        
        return lambda_function
    
    def _create_save_prompt_lambda(self) -> _lambda.Function:
        """Lambda for saving and evaluating admin prompt cards"""
        lambda_function = _lambda.Function(
            self, "SavePromptFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/save_prompt"),
            handler="save_prompt.handler",
            timeout=Duration.seconds(60),
            memory_size=1024,
            environment={
                "ADMIN_PROMPT_CARDS_TABLE": self.admin_prompt_cards_table.table_name,
                "GLOBAL_PROMPT_LIBRARY_TABLE": self.global_prompt_library_table.table_name,
                "PROMPT_EVALUATIONS_TABLE": self.prompt_evaluations_table.table_name,
                "AGENT_THOUGHTS_TABLE": self.agent_thoughts_table.table_name,
                "STEP_CONFIGURATIONS_TABLE": self.step_configurations_table.table_name,
                "PROMPT_EVALUATION_FUNCTION": self.prompt_evaluation_lambda.function_name
            }
        )
        
        # Grant permissions to all prompt-related tables
        self.admin_prompt_cards_table.grant_read_write_data(lambda_function)
        self.global_prompt_library_table.grant_read_write_data(lambda_function)
        self.prompt_evaluations_table.grant_read_write_data(lambda_function)
        self.agent_thoughts_table.grant_read_write_data(lambda_function)
        self.step_configurations_table.grant_read_data(lambda_function)
        
        # Grant Bedrock permissions
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )
        
        # Grant permission to invoke evaluation Lambda
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[self.prompt_evaluation_lambda.function_arn]
            )
        )
        
        return lambda_function
    
    def _create_prompt_evaluation_lambda(self) -> _lambda.Function:
        """Lambda for running LangGraph evaluation workflow"""
        lambda_function = _lambda.Function(
            self, "PromptEvaluationFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/prompt_evaluation"),
            handler="evaluation_workflow.handler",
            timeout=Duration.seconds(300),
            memory_size=2048,
            environment={
                "ADMIN_PROMPT_CARDS_TABLE": self.admin_prompt_cards_table.table_name,
                "GLOBAL_PROMPT_LIBRARY_TABLE": self.global_prompt_library_table.table_name,
                "PROMPT_EVALUATIONS_TABLE": self.prompt_evaluations_table.table_name,
                "AGENT_THOUGHTS_TABLE": self.agent_thoughts_table.table_name,
                "STEP_CONFIGURATIONS_TABLE": self.step_configurations_table.table_name
            }
        )
        
        # Grant permissions to all prompt-related tables
        self.admin_prompt_cards_table.grant_read_write_data(lambda_function)
        self.global_prompt_library_table.grant_read_write_data(lambda_function)
        self.prompt_evaluations_table.grant_read_write_data(lambda_function)
        self.agent_thoughts_table.grant_read_write_data(lambda_function)
        self.step_configurations_table.grant_read_data(lambda_function)
        
        # Grant Bedrock permissions
        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )
        
        return lambda_function
    
    def _create_cors_options_method(self, resource, allowed_methods):
        """CORS OPTIONS 메소드 생성 (기존 스택과 동일)"""
        return resource.add_method(
            "OPTIONS",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                            "method.response.header.Access-Control-Allow-Methods": f"'{allowed_methods}'",
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    )
                ],
                request_templates={"application/json": '{"statusCode": 200}'}
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ],
            authorization_type=apigateway.AuthorizationType.NONE
        )
    
    def _add_gateway_responses(self, api: apigateway.RestApi):
        """Add Gateway Responses for CORS on errors"""
        cors_headers = {
            "method.response.header.Access-Control-Allow-Origin": "'*'",
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'"
        }
        
        # Add CORS headers to common error responses
        api.add_gateway_response(
            "cors-4xx",
            type=apigateway.ResponseType.DEFAULT_4_XX,
            response_headers=cors_headers
        )
        
        api.add_gateway_response(
            "cors-5xx", 
            type=apigateway.ResponseType.DEFAULT_5_XX,
            response_headers=cors_headers
        )
        
        api.add_gateway_response(
            "cors-unauthorized",
            type=apigateway.ResponseType.UNAUTHORIZED,
            response_headers=cors_headers
        )

    def add_api_endpoints(self, api: apigateway.RestApi, authorizer: apigateway.IAuthorizer):
        """Add conversation endpoints to existing API Gateway"""
        
        # /conversations endpoint
        conversations_resource = api.root.add_resource("conversations")
        conversations_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        conversations_resource.add_method(
            "POST", 
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        
        # /conversations/{id} endpoint for individual conversation operations
        conversation_id_resource = conversations_resource.add_resource("{id}")
        conversation_id_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        conversation_id_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(conversations_resource, "GET,POST,OPTIONS")
        self._create_cors_options_method(conversation_id_resource, "DELETE,PUT,OPTIONS")
        
        # /messages endpoint
        messages_resource = api.root.add_resource("messages")
        messages_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.message_lambda),
            authorizer=authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(messages_resource, "GET,OPTIONS")
        
        # Note: /save-prompt endpoint is now handled by BedrockDiyStack
        
        # Add Gateway Responses for CORS on errors
        self._add_gateway_responses(api)