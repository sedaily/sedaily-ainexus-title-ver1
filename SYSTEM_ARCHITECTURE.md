# System Architecture Documentation

## Overview

This document describes the backend architecture for prompt customization, database design for project storage, and the data flow process when users input articles and communicate with Amazon Bedrock.

## 1. Prompt Customization Process

### 1.1 Architecture Components

- **Frontend**: React-based admin interface for prompt management
- **API Gateway**: RESTful endpoints for CRUD operations
- **Lambda Functions**: Serverless compute for business logic
- **DynamoDB**: NoSQL database for prompt metadata
- **S3**: Object storage for prompt content

### 1.2 Data Flow for Prompt Customization

```
Admin User → Frontend → API Gateway → Lambda → DynamoDB (metadata) + S3 (content)
```

#### Create/Update Prompt
1. Admin creates prompt in frontend interface
2. Frontend sends POST/PUT request to `/api/projects/{projectId}/prompts`
3. Lambda function processes request:
   - Generates unique prompt ID
   - Stores prompt metadata in DynamoDB
   - Stores prompt content in S3
4. Returns success response with prompt details

#### Delete Prompt
1. Admin initiates deletion
2. Frontend sends DELETE request to `/api/projects/{projectId}/prompts/{promptId}`
3. Lambda function:
   - Removes entry from DynamoDB
   - Deletes object from S3
4. Returns confirmation

### 1.3 Prompt Storage Structure

#### DynamoDB Schema
```
Table: BedrockDiyPrompts
Primary Key: 
  - projectId (String) - Partition Key
  - promptId (String) - Sort Key

Attributes:
  - title (String)
  - tags (List<String>)
  - createdAt (String)
  - updatedAt (String)
  - isActive (Boolean)
  - stepOrder (Number)
```

#### S3 Structure
```
Bucket: bedrock-diy-prompts-{accountId}-{region}
Path: {projectId}/{promptId}.txt
Content: Plain text prompt content
```

## 2. Project Storage Database Design

### 2.1 Database Schema

#### Projects Table (DynamoDB)
```
Table: BedrockDiyProjects
Primary Key:
  - projectId (String) - Partition Key

Attributes:
  - name (String)
  - description (String)
  - createdAt (String)
  - updatedAt (String)
  - owner (String)
  - settings (Map)
  - status (String) - ACTIVE/INACTIVE
```

#### Chat History Table (DynamoDB)
```
Table: BedrockDiyChatHistory
Primary Key:
  - sessionId (String) - Partition Key
  - timestamp (String) - Sort Key

Attributes:
  - projectId (String)
  - userInput (String)
  - assistantResponse (String)
  - promptCardsUsed (List<String>)
  - processingTime (Number)
```

### 2.2 Data Relationships

- One Project → Many Prompts
- One Project → Many Chat Sessions
- One Chat Session → Many Messages

## 3. Article Processing and Bedrock Communication

### 3.1 Request Flow

```
User Input → WebSocket/HTTP → Lambda → Bedrock → Response Stream → User
```

### 3.2 Detailed Process

#### Step 1: User Input Reception
1. User enters article text in frontend
2. Frontend establishes WebSocket connection or sends HTTP request
3. Request includes:
   - Article content
   - Project ID
   - Chat history (last 50 messages)
   - Active prompt cards

#### Step 2: Prompt Assembly
1. Lambda retrieves active prompts for project
2. Constructs final prompt:
   ```
   System Prompts (from prompt cards)
   + Chat History
   + Current User Input
   ```

#### Step 3: Bedrock API Call
1. Lambda invokes Bedrock with assembled prompt
2. Request configuration:
   ```python
   {
       "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
       "anthropic_version": "bedrock-2023-05-31",
       "max_tokens": 4096,
       "temperature": 0.3,
       "top_p": 0.9,
       "messages": [{"role": "user", "content": final_prompt}]
   }
   ```

#### Step 4: Response Streaming
1. Bedrock returns response stream
2. Lambda processes chunks:
   - WebSocket: Forwards chunks in real-time
   - HTTP SSE: Streams as Server-Sent Events
3. Frontend displays incremental response

### 3.3 Error Handling

- **Timeout**: 2-minute limit for HTTP, configurable for WebSocket
- **Retry Logic**: Automatic retry for transient failures
- **Fallback**: SSE fallback when WebSocket unavailable
- **Error Messages**: User-friendly error responses

### 3.4 Performance Optimization

#### Caching Strategy
- Prompt cards cached in Lambda memory
- Chat history limited to 50 messages
- S3 content accessed via SDK with built-in caching

#### Concurrency Management
- Lambda concurrent execution limit: 1000
- WebSocket connection limit: 25,000
- API Gateway throttling: 10,000 requests/second

## 4. Security Considerations

### 4.1 Authentication & Authorization
- AWS Cognito for user authentication
- IAM roles for service-to-service communication
- API Gateway authorizers for endpoint protection

### 4.2 Data Encryption
- S3: Server-side encryption (SSE-S3)
- DynamoDB: Encryption at rest
- API Gateway: TLS 1.2 for data in transit

### 4.3 Access Control
- Lambda execution role with least privilege
- S3 bucket policies restricting access
- DynamoDB fine-grained access control

## 5. Monitoring and Logging

### 5.1 CloudWatch Integration
- Lambda function logs
- API Gateway access logs
- DynamoDB operation metrics
- S3 access logs

### 5.2 Key Metrics
- Response time percentiles
- Error rates by type
- Bedrock API usage
- WebSocket connection count

## 6. Deployment Architecture

### 6.1 Infrastructure as Code
- AWS CDK for infrastructure definition
- Separate stacks for backend and frontend
- Environment-specific configurations

### 6.2 CI/CD Pipeline
```
Code Push → GitHub → CDK Build → Lambda Package → CloudFormation Deploy
```

### 6.3 Environment Strategy
- Development: Feature testing
- Staging: Pre-production validation
- Production: Live system

## 7. Scalability Considerations

### 7.1 Horizontal Scaling
- Lambda auto-scales based on demand
- DynamoDB on-demand billing mode
- CloudFront for global content delivery

### 7.2 Vertical Scaling
- Lambda memory: 512MB (configurable)
- API Gateway payload limit: 10MB
- WebSocket message size: 128KB

### 7.3 Cost Optimization
- Lambda provisioned concurrency for predictable workloads
- S3 lifecycle policies for old prompts
- DynamoDB TTL for chat history cleanup