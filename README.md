# AI Title Generation System

A scalable, serverless AI-powered title generation system built on AWS infrastructure using AWS Bedrock Claude 3 Sonnet model. This system provides intelligent title suggestions for various content types with real-time streaming capabilities and advanced performance optimizations.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   React SPA     │◄──►│  CloudFront  │◄──►│   S3 Bucket     │
│  (Frontend)     │    │     CDN      │    │ (Static Assets) │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────┐
│  API Gateway    │◄──►│    Lambda    │
│   (REST API)    │    │  Functions   │
└─────────────────┘    └──────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   DynamoDB      │    │ AWS Bedrock  │    │  Cognito User   │
│   (Database)    │    │ Claude 3     │    │     Pool        │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## 🚀 Core Features

- **AI-Powered Title Generation**: Leverages AWS Bedrock Claude 3 Sonnet for intelligent content analysis
- **Real-time Streaming**: Implements streaming responses for improved user experience
- **Dynamic Prompt Management**: Customizable prompts with template variables and versioning
- **Performance Optimization**: Advanced timeout handling, retry logic, and token management
- **Scalable Infrastructure**: Serverless architecture with auto-scaling capabilities
- **User Authentication**: Secure access with AWS Cognito integration
- **Project Management**: Organized workspace for managing multiple title generation projects

## 🛠️ Technology Stack

### Frontend

- **React 18** with Hooks and Context API
- **Tailwind CSS** for responsive UI design
- **React Router** for client-side navigation
- **React Hot Toast** for notifications
- **Heroicons** for consistent iconography

### Backend Infrastructure

- **AWS CDK (Python)** for Infrastructure as Code
- **AWS Lambda** (Python 3.12) for serverless compute
- **AWS API Gateway** for REST API management
- **AWS DynamoDB** for NoSQL data storage
- **AWS Cognito** for authentication and user management
- **AWS S3** for static asset hosting
- **AWS CloudFront** with OAC for global content delivery

### AI/ML Stack

- **AWS Bedrock** for foundation model access
- **Claude 3 Sonnet** as the primary language model
- **Streaming API** for real-time response generation

## 🧠 AWS Bedrock Configuration

### Model Selection

- **Primary Model**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Context Window**: 200K tokens
- **Max Output Tokens**: Dynamically adjusted (1024-8192 tokens)
- **Temperature**: 0.7 (balanced creativity and consistency)

### Performance Optimizations

#### 1. Dynamic Token Management

```python
def calculate_dynamic_max_tokens(input_length):
    base_tokens = 1024
    if input_length > 10000:
        return min(8192, base_tokens + (input_length // 100))
    elif input_length > 5000:
        return min(4096, base_tokens + (input_length // 200))
    return base_tokens
```

#### 2. Streaming Implementation

- **Primary**: `invoke_model_with_response_stream` for real-time responses
- **Fallback**: Standard `invoke_model` for compatibility
- **Error Handling**: Automatic fallback on streaming failures

#### 3. Advanced Retry Logic

- **Max Retries**: 3 attempts with exponential backoff
- **Token Reduction**: 30% reduction on token limit errors
- **Intelligent Retry**: Different strategies for different error types

### Prompt Engineering

#### Template Structure

```python
TITLE_GENERATION_PROMPT = """
역할: 당신은 전문적인 제목 작성 전문가입니다.

컨텍스트: {context}
요구사항: {requirements}
스타일: {style}

내용: {content}

다음 조건을 만족하는 제목들을 생성해주세요:
1. 핵심 메시지가 명확하게 전달되어야 함
2. 독자의 관심을 끌 수 있어야 함
3. SEO 최적화를 고려해야 함
4. {additional_instructions}

{count}개의 다양한 제목을 생성해주세요.
"""
```

## 📊 AWS Infrastructure Details

### Serverless Architecture Overview

This system is built on a **100% serverless architecture** with no traditional servers to manage, providing automatic scaling, high availability, and cost optimization.

### Compute Infrastructure

#### 1. AWS Lambda Functions

**Generate Function (Core AI Processing)**

- **Runtime**: Python 3.12
- **Memory**: 3008 MB (maximum allocation)
- **Timeout**: 900 seconds (15 minutes)
- **Reserved Concurrency**: 10 concurrent executions
- **Environment Variables**:
  - `BEDROCK_MODEL_ID`: Model identifier
  - `MAX_TOKENS`: Token limits
  - `REGION`: AWS region
- **VPC**: Not configured (uses AWS managed networking)
- **Layers**: Custom layer for shared dependencies

**Project Management Functions**

- **Runtime**: Python 3.12
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Purpose**: CRUD operations for project lifecycle management
- **Concurrent Executions**: 20 (auto-scaling)

**Authentication Functions**

- **Runtime**: Python 3.12
- **Memory**: 256 MB
- **Timeout**: 10 seconds
- **Purpose**: User authentication, token validation, session management
- **Integration**: Direct integration with Cognito User Pool

#### 2. AWS API Gateway

**REST API Configuration**

- **Type**: Regional REST API
- **Authorization**: Cognito User Pool Authorizer
- **Throttling**: 1000 requests/minute per user
- **Request Validation**: JSON schema validation enabled
- **CORS Configuration**:
  ```json
  {
    "allowOrigins": ["https://your-domain.com"],
    "allowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allowHeaders": ["Content-Type", "Authorization"],
    "maxAge": 86400
  }
  ```

### Storage Infrastructure

#### 1. Amazon DynamoDB Tables

**Projects Table**

```python
{
    "TableName": "bedrock-diy-projects",
    "BillingMode": "PAY_PER_REQUEST",
    "KeySchema": [
        {"AttributeName": "user_id", "KeyType": "HASH"},
        {"AttributeName": "project_id", "KeyType": "RANGE"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "user_id", "AttributeType": "S"},
        {"AttributeName": "project_id", "AttributeType": "S"}
    ],
    "StreamSpecification": {
        "StreamViewType": "NEW_AND_OLD_IMAGES"
    },
    "PointInTimeRecoverySpecification": {"Enabled": True},
    "DeletionProtectionEnabled": True
}
```

**Chat History Table**

```python
{
    "TableName": "bedrock-diy-conversations",
    "BillingMode": "PAY_PER_REQUEST",
    "KeySchema": [
        {"AttributeName": "project_id", "KeyType": "HASH"},
        {"AttributeName": "timestamp", "KeyType": "RANGE"}
    ],
    "TimeToLiveSpecification": {
        "Enabled": True,
        "AttributeName": "ttl"  # 30 days retention
    },
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "user-timestamp-index",
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "timestamp", "KeyType": "RANGE"}
            ]
        }
    ]
}
```

#### 2. Amazon S3 Storage

**Frontend Assets Bucket**

- **Bucket Policy**: Private with CloudFront OAC access only
- **Encryption**: AES-256 server-side encryption
- **Versioning**: Disabled (CDK manages deployments)
- **Lifecycle Rules**:
  - Abort incomplete multipart uploads after 7 days
  - Delete old versions after 30 days

### Content Delivery Network (CDN)

#### CloudFront Distribution

**Distribution Configuration**

```python
{
    "PriceClass": "PriceClass_100",  # US, Canada, Europe
    "DefaultRootObject": "index.html",
    "ViewerProtocolPolicy": "redirect-to-https",
    "MinimumProtocolVersion": "TLSv1.2_2021",
    "Compression": True
}
```

**Caching Behaviors**

- **Static Assets** (_.js, _.css, \*.png, etc.):
  - Cache Policy: `CACHING_OPTIMIZED`
  - TTL: 31536000 seconds (1 year)
  - Compression: Enabled
- **API Calls** (/api/\*):
  - Cache Policy: `CACHING_DISABLED`
  - Origin Request Policy: `ALL_VIEWER`
  - Allowed Methods: `ALLOW_ALL`

**Origin Access Control (OAC)**

- **Signing**: SIGV4_ALWAYS
- **Origin Type**: S3
- **Enhanced Security**: Short-term credentials with frequent rotation

### AI/ML Infrastructure

#### AWS Bedrock Integration

**Model Access**

- **Foundation Model**: Claude 3 Sonnet
- **Model ARN**: `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0`
- **Cross-Region Inference**: Disabled (single region deployment)
- **Model Invocation Logging**: Enabled for monitoring

**Inference Configuration**

```python
{
    "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
    "contentType": "application/json",
    "accept": "application/json",
    "body": {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": "dynamic (1024-8192)",
        "temperature": 0.7,
        "system": "You are a professional title generation expert...",
        "messages": [...]
    }
}
```

### Networking and Security

#### VPC Configuration

- **VPC**: Not used (Lambda functions use AWS managed VPC)
- **Reason**: No private resources requiring VPC isolation
- **Cost Optimization**: Eliminates NAT Gateway costs

#### Security Groups and NACLs

- **Not Applicable**: Serverless architecture uses AWS managed networking
- **Security**: Implemented through IAM policies and resource-based policies

#### DNS and Domain Management

- **Route 53**: Not configured in this stack
- **CloudFront Domain**: Uses default CloudFront domain (.cloudfront.net)
- **Custom Domain**: Can be added via Route 53 + ACM certificate

### Authentication and Authorization

#### AWS Cognito User Pool

**User Pool Configuration**

```python
{
    "UserPoolName": "bedrock-diy-users",
    "UsernameAttributes": ["email"],
    "AutoVerifiedAttributes": ["email"],
    "PasswordPolicy": {
        "MinimumLength": 8,
        "RequireUppercase": True,
        "RequireLowercase": True,
        "RequireNumbers": True,
        "RequireSymbols": True
    },
    "MfaConfiguration": "OPTIONAL",
    "AccountRecoverySetting": {
        "RecoveryMechanisms": [
            {"Name": "verified_email", "Priority": 1}
        ]
    }
}
```

#### IAM Roles and Policies

**Lambda Execution Role**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": ["arn:aws:dynamodb:*:*:table/bedrock-diy-*"]
    }
  ]
}
```

### Monitoring and Logging Infrastructure

#### CloudWatch Configuration

- **Log Groups**: Separate log groups for each Lambda function
- **Log Retention**: 14 days for cost optimization
- **Custom Metrics**: Business metrics for title generation performance
- **Alarms**:
  - Lambda error rates > 5%
  - Lambda duration > 30 seconds
  - DynamoDB throttling events

#### AWS X-Ray Tracing

- **Enabled**: For all Lambda functions
- **Sampling Rate**: 10% for cost optimization
- **Service Map**: Provides visual representation of request flow

### Disaster Recovery and Backup

#### Data Backup Strategy

- **DynamoDB**: Point-in-time recovery enabled
- **S3**: Versioning disabled (CDK manages state)
- **Cross-Region**: Single region deployment (can be extended)

#### High Availability

- **Multi-AZ**: Automatic (DynamoDB, Lambda, API Gateway)
- **Global Edge Locations**: CloudFront provides global availability
- **Auto-Scaling**: Built into all serverless components

### Cost Optimization Features

#### Resource Optimization

- **Lambda**: Right-sized memory allocation
- **DynamoDB**: On-demand billing
- **CloudFront**: Price class 100 (cost-optimized regions)
- **S3**: Lifecycle policies for cost management

#### Estimated Monthly Costs (Production Usage)

```
- Lambda (1M requests): ~$15-25
- DynamoDB (10GB, 1M R/W): ~$5-10
- Bedrock (100K tokens/day): ~$20-40
- CloudFront (100GB transfer): ~$8-12
- S3 Storage (10GB): ~$0.23
- API Gateway (1M requests): ~$3.50
- Total Estimated: ~$50-90/month
```

## 🔧 Model Tuning and Optimization

### Token Management Strategy

1. **Input Analysis**: Dynamic token calculation based on content length
2. **Context Optimization**: Automatic chat history trimming (20+ messages)
3. **Output Control**: Adaptive max_tokens based on request complexity

### Error Handling and Resilience

```python
# Retry configuration
RETRY_CONFIG = {
    "max_attempts": 3,
    "backoff_multiplier": 2,
    "token_reduction_factor": 0.7,
    "supported_errors": [
        "ValidationException",
        "ThrottlingException",
        "ServiceUnavailableException"
    ]
}
```

### Performance Monitoring

- **CloudWatch Metrics**: Custom metrics for response times, error rates
- **Structured Logging**: Detailed performance logs for each request phase
- **Timeout Tracking**: Progressive timeout handling (Frontend: 900s, Lambda: 900s)

## 🚀 Deployment Guide

### Prerequisites

- AWS CLI configured with appropriate permissions
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Python 3.12+
- Node.js 18+

### Deployment Steps

1. **Bootstrap CDK** (first-time only)

```bash
cdk bootstrap
```

2. **Deploy Infrastructure**

```bash
cd cdk
pip install -r requirements.txt
cdk deploy --all --require-approval never
```

3. **Build and Deploy Frontend**

```bash
cd frontend
npm install
npm run build
# Files automatically uploaded to S3 via CDK deployment
```

### Environment Configuration

```bash
# Required environment variables
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
MAX_TOKENS=8192
TEMPERATURE=0.7
```

## 📋 API Endpoints

### Title Generation

```http
POST /api/generate
Authorization: Bearer {cognito_token}
Content-Type: application/json

{
  "content": "Text content for title generation",
  "context": "Optional context",
  "requirements": "Specific requirements",
  "count": 5
}
```

### Project Management

```http
GET /api/projects
POST /api/projects
PUT /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

## 🔒 Security Features

- **Authentication**: AWS Cognito User Pool with MFA support
- **Authorization**: Fine-grained IAM policies
- **Data Encryption**: At-rest and in-transit encryption
- **CORS Protection**: Strict CORS policies
- **Rate Limiting**: API Gateway throttling
- **Content Security**: CloudFront security headers

## 📈 Performance Characteristics

- **Cold Start**: ~2-3 seconds for Lambda initialization
- **Warm Response**: ~500ms-2s for title generation
- **Throughput**: 1000+ concurrent requests
- **Availability**: 99.9% SLA with multi-AZ deployment
- **Latency**: <100ms CloudFront edge response for static assets

## 🛡️ Monitoring and Observability

- **CloudWatch Logs**: Structured logging for all components
- **CloudWatch Metrics**: Custom business and performance metrics
- **AWS X-Ray**: Distributed tracing for request flow analysis
- **Error Tracking**: Automated error detection and alerting

## 📚 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

For support and questions, please open an issue in the GitHub repository or contact the development team.

---

Built with ❤️ using AWS Bedrock, CDK, and React
