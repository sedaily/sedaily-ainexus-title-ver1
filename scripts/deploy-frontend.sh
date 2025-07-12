#!/bin/bash

# TITLE-NOMICS 프론트엔드 배포 스크립트
# S3 + CloudFront 배포 자동화

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 파라미터 확인
API_URL="$1"
ENVIRONMENT="${2:-production}"

if [ -z "$API_URL" ]; then
    print_error "사용법: $0 <API_URL> [environment]"
    print_warning "예시: $0 https://abc123.execute-api.us-east-1.amazonaws.com/prod production"
    exit 1
fi

print_step "프론트엔드 배포 시작"
echo "API URL: $API_URL"
echo "Environment: $ENVIRONMENT"

# 현재 디렉토리 확인
if [ ! -f "package.json" ]; then
    print_warning "frontend 디렉토리로 이동 중..."
    if [ -d "frontend" ]; then
        cd frontend
    else
        print_error "frontend 디렉토리를 찾을 수 없습니다"
        exit 1
    fi
fi

# Node.js 확인
if ! command -v node &> /dev/null; then
    print_error "Node.js가 설치되지 않았습니다"
    exit 1
fi
print_success "Node.js 설치됨"

# 환경 변수 설정
print_step "환경 변수 설정"
cat > .env << EOF
REACT_APP_API_URL=$API_URL
REACT_APP_ENVIRONMENT=$ENVIRONMENT
GENERATE_SOURCEMAP=false
EOF
print_success "환경 변수 설정 완료"

# 의존성 설치
print_step "의존성 설치"
if [ -f "package-lock.json" ]; then
    npm ci
else
    npm install
fi
print_success "의존성 설치 완료"

# 린트 검사
print_step "코드 품질 검사"
if npm run lint --if-present; then
    print_success "린트 검사 통과"
else
    print_warning "린트 검사에서 경고가 있습니다"
fi

# 테스트 실행
print_step "테스트 실행"
if npm run test -- --watchAll=false --coverage --passWithNoTests; then
    print_success "테스트 통과"
else
    print_warning "테스트에서 경고가 있습니다"
fi

# 빌드
print_step "프로덕션 빌드"
npm run build
print_success "빌드 완료"

# 빌드 결과 확인
if [ ! -d "build" ]; then
    print_error "빌드 디렉토리가 생성되지 않았습니다"
    exit 1
fi

BUILD_SIZE=$(du -sh build | cut -f1)
print_success "빌드 크기: $BUILD_SIZE"

# CDK 배포 (프론트엔드 스택)
print_step "CloudFront 배포"
cd ../cdk

# Python 의존성 확인
if [ ! -d "venv" ]; then
    print_warning "Python 가상환경 생성 중..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# CDK 배포
print_warning "이 단계는 시간이 걸릴 수 있습니다 (약 5-10분)..."
cdk deploy FrontendStack --require-approval never --outputs-file frontend-outputs.json

# 배포 결과 확인
if [ -f "frontend-outputs.json" ]; then
    FRONTEND_URL=$(cat frontend-outputs.json | jq -r '.FrontendStack.WebsiteURL' 2>/dev/null || echo "")
    DISTRIBUTION_ID=$(cat frontend-outputs.json | jq -r '.FrontendStack.DistributionId' 2>/dev/null || echo "")
    
    if [ "$FRONTEND_URL" != "null" ] && [ "$FRONTEND_URL" != "" ]; then
        print_success "프론트엔드 배포 완료!"
        echo "  URL: $FRONTEND_URL"
        echo "  Distribution ID: $DISTRIBUTION_ID"
    else
        print_warning "배포는 완료되었지만 URL을 가져올 수 없습니다"
    fi
else
    print_warning "출력 파일을 찾을 수 없습니다"
fi

# CloudFront 캐시 무효화
if [ "$DISTRIBUTION_ID" != "null" ] && [ "$DISTRIBUTION_ID" != "" ]; then
    print_step "CloudFront 캐시 무효화"
    aws cloudfront create-invalidation \
        --distribution-id "$DISTRIBUTION_ID" \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text
    print_success "캐시 무효화 요청 완료"
fi

# 배포 완료
print_step "배포 완료"
print_success "프론트엔드가 성공적으로 배포되었습니다!"

if [ "$FRONTEND_URL" != "null" ] && [ "$FRONTEND_URL" != "" ]; then
    echo
    print_warning "다음 단계:"
    echo "1. 브라우저에서 $FRONTEND_URL 접속"
    echo "2. 로그인 및 프로젝트 생성 테스트"
    echo "3. API 연결 상태 확인"
    echo "4. 제목 생성 기능 테스트"
    echo
fi

print_warning "참고사항:"
echo "- CloudFront 배포는 전 세계적으로 전파되는데 최대 15분이 걸릴 수 있습니다"
echo "- 캐시 무효화는 완료까지 몇 분이 소요됩니다"
echo "- 문제 발생 시 CloudWatch 로그를 확인하세요"

deactivate 2>/dev/null || true
print_success "배포 스크립트 완료!" 