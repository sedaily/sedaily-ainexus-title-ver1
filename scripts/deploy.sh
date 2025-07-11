#!/bin/bash

# 🚀 TITLE-NOMICS + LangChain 채팅 히스토리 빠른 배포 스크립트
# "금붕어 LLM"에게 기억력을 선사하는 업그레이드!

set -e

echo "🚀 TITLE-NOMICS + LangChain 채팅 기능 배포 시작..."
echo "💭 이제 AI가 이전 대화를 기억합니다! (90일 TTL로 지갑도 기억해요)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_memory() {
    echo -e "${PURPLE}🧠 $1${NC}"
}

# 사전 요구사항 확인
print_step "사전 요구사항 확인"

# AWS CLI 확인
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI가 설치되지 않았습니다"
    exit 1
fi
print_success "AWS CLI 설치됨"

# AWS 자격증명 확인
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS 자격증명이 구성되지 않았습니다"
    exit 1
fi
print_success "AWS 자격증명 구성됨"

# Node.js 확인
if ! command -v node &> /dev/null; then
    print_error "Node.js가 설치되지 않았습니다"
    exit 1
fi
print_success "Node.js 설치됨"

# Python 확인
if ! command -v python3 &> /dev/null; then
    print_error "Python3가 설치되지 않았습니다"
    exit 1
fi
print_success "Python3 설치됨"

# CDK 확인
if ! command -v cdk &> /dev/null; then
    print_warning "CDK가 설치되지 않았습니다. 설치 중..."
    npm install -g aws-cdk
fi
print_success "CDK 설치됨"

# 🆕 LangChain 메모리 기능 안내
print_step "LangChain 메모리 기능 안내"
print_memory "추가된 기능들:"
echo "  💬 대화 히스토리 (DynamoDB + 90일 TTL)"
echo "  🧠 ConversationSummaryBufferMemory (최근 6턴 + 요약)"
echo "  🔍 OpenSearch 기반 관련 메시지 RAG"
echo "  📊 메모리 버퍼 크기 및 토큰 사용량 모니터링"
echo "  🔄 Claude 3.5 Sonnet (메인) + Titan Lite (요약)"

# Bedrock 모델 액세스 확인
print_step "Bedrock 모델 액세스 확인"
print_warning "AWS 콘솔에서 다음 모델들이 활성화되어 있는지 확인하세요:"
echo "  - Claude 3.5 Sonnet (메인 채팅용)"
echo "  - Claude 3.5 Sonnet v2 (제목 생성용)"
echo "  - Titan Embeddings (벡터 검색용)"
echo "  - Titan Text Lite (요약용) 🆕"
echo "  - 활성화 후 Enter를 누르세요..."
read -p ""

# CDK 부트스트랩
print_step "CDK 부트스트랩"
cd cdk
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    print_warning "CDK 부트스트랩 실행 중..."
    cdk bootstrap
    print_success "CDK 부트스트랩 완료"
else
    print_success "CDK 이미 부트스트랩됨"
fi

# Python 의존성 설치
print_step "Python 의존성 설치"
pip install -r requirements.txt
print_success "Python 의존성 설치 완료"

# 🆕 LangChain Lambda 의존성 사전 설치
print_step "LangChain Lambda 의존성 설치"
if [ -d "../lambda/langchain_router" ]; then
    cd ../lambda/langchain_router
    print_memory "LangChain 패키지 설치 중... (시간이 좀 걸릴 수 있어요)"
    pip install -r requirements.txt -t .
    print_success "LangChain 의존성 설치 완료"
    cd ../../cdk
else
    print_warning "LangChain 라우터 디렉토리를 찾을 수 없습니다"
fi

# CDK 배포
print_step "AWS 인프라 배포 (채팅 기능 포함)"
print_warning "이 단계는 시간이 걸릴 수 있습니다 (약 15-20분)..."
print_memory "새로 생성되는 리소스:"
echo "  📦 DynamoDB: bedrock-diy-chat-history (채팅 히스토리)"
echo "  📦 DynamoDB: bedrock-diy-chat-sessions (세션 메타데이터)"
echo "  🔧 Lambda: bedrock-diy-langchain-router (2048MB 메모리)"
echo "  🌐 API Gateway: /projects/{id}/chat 엔드포인트"

cdk deploy --require-approval never

# 출력값 가져오기
print_step "배포 결과 확인"
API_URL=$(aws cloudformation describe-stacks --stack-name BedrockDiyStack --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' --output text)
PROMPT_BUCKET=$(aws cloudformation describe-stacks --stack-name BedrockDiyStack --query 'Stacks[0].Outputs[?OutputKey==`PromptBucketName`].OutputValue' --output text)
OPENSEARCH_ENDPOINT=$(aws cloudformation describe-stacks --stack-name BedrockDiyStack --query 'Stacks[0].Outputs[?OutputKey==`OpenSearchEndpoint`].OutputValue' --output text)
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks --stack-name BedrockDiyStack --query 'Stacks[0].Outputs[?OutputKey==`StateMachineArn`].OutputValue' --output text)

print_success "API Gateway URL: $API_URL"
print_success "Prompt Bucket: $PROMPT_BUCKET"
print_success "OpenSearch Endpoint: $OPENSEARCH_ENDPOINT"
print_success "State Machine ARN: $STATE_MACHINE_ARN"

# 🆕 채팅 테이블 확인
print_step "채팅 기능 테이블 확인"
CHAT_HISTORY_TABLE=$(aws dynamodb describe-table --table-name bedrock-diy-chat-history --query 'Table.TableName' --output text 2>/dev/null || echo "NOT_FOUND")
CHAT_SESSION_TABLE=$(aws dynamodb describe-table --table-name bedrock-diy-chat-sessions --query 'Table.TableName' --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$CHAT_HISTORY_TABLE" != "NOT_FOUND" ]; then
    print_success "채팅 히스토리 테이블: $CHAT_HISTORY_TABLE"
else
    print_error "채팅 히스토리 테이블 생성 실패"
fi

if [ "$CHAT_SESSION_TABLE" != "NOT_FOUND" ]; then
    print_success "채팅 세션 테이블: $CHAT_SESSION_TABLE"
else
    print_error "채팅 세션 테이블 생성 실패"
fi

# 프론트엔드 배포
print_step "프론트엔드 배포"
cd ../frontend

# 환경 변수 설정
echo "REACT_APP_API_URL=$API_URL" > .env
print_success "환경 변수 설정 완료"

# 의존성 설치
print_step "프론트엔드 의존성 설치"
npm install
print_success "프론트엔드 의존성 설치 완료"

# 빌드
print_step "프론트엔드 빌드"
npm run build
print_success "프론트엔드 빌드 완료"

# 개발 서버 실행 (백그라운드)
print_step "개발 서버 실행"
nohup npm start > /dev/null 2>&1 &
DEV_SERVER_PID=$!
print_success "개발 서버 실행 중 (PID: $DEV_SERVER_PID)"

# 배포 완료 메시지
print_step "배포 완료! 🎉"
echo
print_success "백엔드 배포 완료:"
echo "  - API Gateway: $API_URL"
echo "  - Step Functions: $STATE_MACHINE_ARN"
echo "  - OpenSearch: $OPENSEARCH_ENDPOINT"
echo "  - Prompt Bucket: $PROMPT_BUCKET"
echo "  - 채팅 히스토리: $CHAT_HISTORY_TABLE"
echo "  - 채팅 세션: $CHAT_SESSION_TABLE"
echo
print_success "프론트엔드 배포 완료:"
echo "  - 개발 서버: http://localhost:3000"
echo "  - 빌드 파일: ./build/"
echo

print_memory "🧠 LangChain 메모리 기능 특징:"
echo "  ✨ 대화 컨텍스트 자동 관리 (최근 6턴 + 요약)"
echo "  🔍 관련 과거 대화 검색 (OpenSearch k-NN)"
echo "  💰 토큰 비용 최적화 (요약으로 컨텍스트 압축)"
echo "  🗑️ 자동 TTL (90일 후 채팅 히스토리 삭제)"
echo "  📊 메모리 버퍼 상태 실시간 표시"
echo

print_warning "다음 단계:"
echo "1. 브라우저에서 http://localhost:3000 접속"
echo "2. 새 프로젝트 생성"
echo "3. 11개 카테고리 프롬프트 업로드"
echo "4. '제목 생성'으로 기본 제목 생성 테스트"
echo "5. 🆕 'AI 채팅'으로 대화형 제목 상담 테스트"
echo

print_warning "채팅 기능 테스트:"
echo "1. 'AI 채팅' 탭 클릭"
echo "2. '새 채팅 시작' 버튼 클릭"  
echo "3. '이 기사 제목을 어떻게 개선할 수 있을까요?' 질문"
echo "4. 대화 이어가기 (LangChain이 이전 대화 기억)"
echo "5. 세션 삭제 및 새 세션 생성 테스트"
echo

print_warning "비용 모니터링 (업데이트):"
echo "- CloudWatch 대시보드에서 비용 확인"
echo "- 월 $1000 예산 알람 설정됨"
echo "- 🆕 채팅 히스토리 TTL: 90일 (자동 삭제)"
echo "- 🆕 LangChain Lambda 메모리: 2GB (비용 약간 증가)"
echo "- 사용하지 않을 때는 'cdk destroy' 실행"
echo    

print_success "배포 완료! 이제 AI와 대화하며 제목을 생성하세요! 🚀💬"
echo "❓ 문제 발생 시 CloudWatch 로그를 확인하세요."
echo "📧 심각한 오류는 SNS 알림으로 전송됩니다."
echo "🧠 채팅 메모리 문제는 langchain-router Lambda 로그 확인"

# 테스트 스크립트 생성 (채팅 기능 포함)
print_step "테스트 스크립트 생성"
cat > ../test-api.sh << 'EOF'
#!/bin/bash

# API 테스트 스크립트 (채팅 기능 포함)
API_URL="$1"

if [ -z "$API_URL" ]; then
    echo "사용법: $0 <API_URL>"
    exit 1
fi

echo "🧪 API 테스트 시작..."

# 프로젝트 생성 테스트
echo "1. 프로젝트 생성 테스트..."
PROJECT_RESPONSE=$(curl -s -X POST "$API_URL/projects" \
    -H "Content-Type: application/json" \
    -d '{"name": "채팅 테스트 프로젝트", "description": "LangChain 채팅 테스트용"}')

PROJECT_ID=$(echo $PROJECT_RESPONSE | jq -r '.projectId')
echo "   프로젝트 ID: $PROJECT_ID"

# 채팅 세션 테스트
echo "2. 채팅 세션 테스트..."
CHAT_RESPONSE=$(curl -s -X POST "$API_URL/projects/$PROJECT_ID/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "안녕하세요! 제목 생성에 대해 궁금합니다.", "userId": "testuser"}')

echo "   채팅 응답:"
echo $CHAT_RESPONSE | jq '.'

SESSION_ID=$(echo $CHAT_RESPONSE | jq -r '.sessionId')
echo "   세션 ID: $SESSION_ID"

# 채팅 세션 목록 테스트
echo "3. 채팅 세션 목록 테스트..."
curl -s "$API_URL/projects/$PROJECT_ID/chat/sessions" | jq '.'

echo "✅ API 테스트 완료!"
EOF

chmod +x ../test-api.sh
print_success "테스트 스크립트 생성: ../test-api.sh"

echo
print_memory "🎯 목표 달성! '금붕어 LLM'이 이제 코끼리 기억력을 갖췄습니다! 🐘💭"
echo
print_warning "참고: 개발 서버를 중지하려면 'kill $DEV_SERVER_PID' 실행"
print_warning "LangChain 메모리 이슈 시: Lambda 메모리 크기 조정 또는 타임아웃 연장 고려" 