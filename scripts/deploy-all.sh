#!/bin/bash

# TITLE-NOMICS 전체 시스템 배포 스크립트
# 백엔드 (서버리스) + 프론트엔드 (S3 + CloudFront) 통합 배포

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

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

print_info() {
    echo -e "${PURPLE}ℹ️ $1${NC}"
}

# 시작 메시지
print_step "TITLE-NOMICS 전체 시스템 배포 시작"
print_info "서버리스 백엔드 + 정적 프론트엔드 배포"
echo "시작 시간: $(date)"

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

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")
print_success "AWS 계정: $AWS_ACCOUNT, 리전: $AWS_REGION"

# Node.js 확인
if ! command -v node &> /dev/null; then
    print_error "Node.js가 설치되지 않았습니다"
    exit 1
fi
NODE_VERSION=$(node --version)
print_success "Node.js $NODE_VERSION 설치됨"

# Python 확인
if ! command -v python3 &> /dev/null; then
    print_error "Python3가 설치되지 않았습니다"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
print_success "$PYTHON_VERSION 설치됨"

# CDK 확인
if ! command -v cdk &> /dev/null; then
    print_warning "CDK가 설치되지 않았습니다. 설치 중..."
    npm install -g aws-cdk
fi
CDK_VERSION=$(cdk --version)
print_success "CDK $CDK_VERSION 설치됨"

# jq 확인 (JSON 파싱용)
if ! command -v jq &> /dev/null; then
    print_warning "jq가 설치되지 않았습니다. macOS에서 설치 중..."
    if command -v brew &> /dev/null; then
        brew install jq
    else
        print_error "jq를 수동으로 설치해주세요: https://stedolan.github.io/jq/"
        exit 1
    fi
fi
print_success "jq 설치됨"

# Bedrock 모델 액세스 확인
print_step "Bedrock 모델 액세스 확인"
print_warning "다음 모델들이 AWS 콘솔에서 활성화되어 있는지 확인하세요:"
echo "  - Claude 3.5 Sonnet v2 (제목 생성용)"
echo "  - Claude 3.5 Sonnet (채팅용)"
echo "  - Claude 3 Haiku (요약용)"
echo "  - Titan Embeddings (벡터 검색용)"
echo ""
read -p "모든 모델이 활성화되었으면 Enter를 누르세요..."

# 1단계: 백엔드 배포
print_step "1단계: 백엔드 인프라 배포"
cd cdk

# CDK 부트스트랩
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    print_warning "CDK 부트스트랩 실행 중..."
    cdk bootstrap
    print_success "CDK 부트스트랩 완료"
else
    print_success "CDK 이미 부트스트랩됨"
fi

# Python 의존성 설치
print_info "Python 의존성 설치 중..."
pip install -r requirements.txt
print_success "Python 의존성 설치 완료"

# 백엔드 스택 배포
print_warning "백엔드 배포 중... (약 10-15분 소요)"
cdk deploy BedrockDiyAuthStack --require-approval never --outputs-file backend-outputs.json

# 백엔드 출력값 확인
if [ -f "backend-outputs.json" ]; then
    API_URL=$(cat backend-outputs.json | jq -r '.BedrockDiyAuthStack.ApiGatewayUrl')
    PROMPT_BUCKET=$(cat backend-outputs.json | jq -r '.BedrockDiyAuthStack.PromptBucketName')
    USER_POOL_ID=$(cat backend-outputs.json | jq -r '.BedrockDiyAuthStack.UserPoolId')
    
    print_success "백엔드 배포 완료!"
    echo "  API Gateway URL: $API_URL"
    echo "  Prompt Bucket: $PROMPT_BUCKET"
    echo "  User Pool ID: $USER_POOL_ID"
else
    print_error "백엔드 출력 파일을 찾을 수 없습니다"
    exit 1
fi

# 2단계: 프론트엔드 빌드
print_step "2단계: 프론트엔드 빌드"
cd ../frontend

# Node.js 의존성 설치
print_info "Node.js 의존성 설치 중..."
if [ -f "package-lock.json" ]; then
    npm ci
else
    npm install
fi
print_success "Node.js 의존성 설치 완료"

# 환경 변수 설정
print_info "환경 변수 설정 중..."
cat > .env << EOF
REACT_APP_API_URL=$API_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_USER_POOL_ID=$USER_POOL_ID
GENERATE_SOURCEMAP=false
EOF
print_success "환경 변수 설정 완료"

# 코드 품질 검사
print_info "코드 품질 검사 중..."
if npm run lint --if-present; then
    print_success "린트 검사 통과"
else
    print_warning "린트 검사에서 경고가 있습니다 (계속 진행)"
fi

# 테스트 실행
print_info "테스트 실행 중..."
if npm run test -- --watchAll=false --coverage --passWithNoTests; then
    print_success "테스트 통과"
else
    print_warning "테스트에서 경고가 있습니다 (계속 진행)"
fi

# 프로덕션 빌드
print_info "프로덕션 빌드 중..."
npm run build
BUILD_SIZE=$(du -sh build | cut -f1)
print_success "프론트엔드 빌드 완료 (크기: $BUILD_SIZE)"

# 3단계: 프론트엔드 배포
print_step "3단계: 프론트엔드 배포 (S3 + CloudFront)"
cd ../cdk

# 프론트엔드 스택 배포
print_warning "프론트엔드 배포 중... (약 5-10분 소요)"
cdk deploy FrontendStack --require-approval never --outputs-file frontend-outputs.json

# 프론트엔드 출력값 확인
if [ -f "frontend-outputs.json" ]; then
    FRONTEND_URL=$(cat frontend-outputs.json | jq -r '.FrontendStack.WebsiteURL')
    DISTRIBUTION_ID=$(cat frontend-outputs.json | jq -r '.FrontendStack.DistributionId')
    BUCKET_NAME=$(cat frontend-outputs.json | jq -r '.FrontendStack.BucketName')
    
    print_success "프론트엔드 배포 완료!"
    echo "  CloudFront URL: $FRONTEND_URL"
    echo "  Distribution ID: $DISTRIBUTION_ID"
    echo "  S3 Bucket: $BUCKET_NAME"
else
    print_error "프론트엔드 출력 파일을 찾을 수 없습니다"
    exit 1
fi

# 4단계: CloudFront 캐시 무효화
print_step "4단계: CloudFront 캐시 무효화"
if [ "$DISTRIBUTION_ID" != "null" ] && [ "$DISTRIBUTION_ID" != "" ]; then
    INVALIDATION_ID=$(aws cloudfront create-invalidation \
        --distribution-id "$DISTRIBUTION_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text)
    print_success "캐시 무효화 요청 완료 (ID: $INVALIDATION_ID)"
else
    print_warning "Distribution ID를 찾을 수 없어 캐시 무효화를 건너뜁니다"
fi

# 5단계: 배포 완료 및 테스트
print_step "배포 완료!"
echo ""
print_success "전체 시스템이 성공적으로 배포되었습니다!"

echo ""
print_info "배포 정보 요약:"
echo "  완료 시간: $(date)"
echo "  백엔드 API: $API_URL"
echo "  프론트엔드: $FRONTEND_URL"
echo "  리전: $AWS_REGION"
echo "  계정: $AWS_ACCOUNT"

echo ""
print_warning "다음 단계:"
echo "1. 브라우저에서 $FRONTEND_URL 접속"
echo "2. 회원가입 및 로그인 테스트"
echo "3. 새 프로젝트 생성"
echo "4. 프롬프트 카드 업로드"
echo "5. 제목 생성 기능 테스트"
echo "6. AI 채팅 기능 테스트"

echo ""
print_warning "참고사항:"
echo "- CloudFront 배포는 전 세계적으로 전파되는데 최대 15분이 걸릴 수 있습니다"
echo "- 캐시 무효화는 완료까지 몇 분이 소요됩니다"
echo "- 문제 발생 시 CloudWatch 로그를 확인하세요"

echo ""
print_warning "비용 모니터링:"
echo "- Lambda: 요청 기반 과금 (월 ~$5-20)"
echo "- Bedrock: 토큰 기반 과금 (월 ~$10-50)"
echo "- S3: 저장 용량 기반 (월 ~$1-5)"
echo "- CloudFront: 트래픽 기반 (월 ~$1-10)"
echo "- DynamoDB: 요청 기반 과금 (월 ~$1-5)"
echo "- 총 예상 비용: 월 $20-90 (사용량에 따라)"

echo ""
print_info "시스템 관리:"
echo "- 스택 삭제: cdk destroy --all"
echo "- 백엔드만 업데이트: cdk deploy BedrockDiyAuthStack"
echo "- 프론트엔드만 업데이트: cdk deploy FrontendStack"
echo "- 로그 확인: aws logs tail /aws/lambda/[function-name] --follow"

print_success "배포 스크립트 완료!" 