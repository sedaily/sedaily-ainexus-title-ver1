#!/bin/bash

# 새 프로젝트 설정 스크립트
# 사용법: ./scripts/setup-new-project.sh

set -e

echo "🚀 새 프로젝트 설정 시작"
echo "========================="

# 프로젝트 이름 입력
read -p "프로젝트 이름 (예: my-service): " PROJECT_NAME
read -p "프로젝트 표시 이름 (예: My Service): " PROJECT_DISPLAY_NAME
read -p "스택 접두사 (CamelCase, 예: MyService): " STACK_PREFIX
read -p "AWS 계정 ID: " AWS_ACCOUNT_ID
read -p "AWS 리전 (기본값: ap-northeast-2): " AWS_REGION
AWS_REGION=${AWS_REGION:-ap-northeast-2}

# .env.local 파일 생성
echo "📝 환경 설정 파일 생성 중..."
cat > .env.local << EOF
# 프로젝트 설정
PROJECT_NAME=$PROJECT_NAME
PROJECT_PREFIX=$PROJECT_NAME
PROJECT_DISPLAY_NAME="$PROJECT_DISPLAY_NAME"
PROJECT_DESCRIPTION="$PROJECT_DISPLAY_NAME AI Service"

# AWS 설정
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION

# 스택 이름 설정
STACK_PREFIX=$STACK_PREFIX

# 환경 설정
ENVIRONMENT=dev
EOF

# frontend/.env 파일 생성
echo "📝 프론트엔드 환경 설정 파일 생성 중..."
cat > frontend/.env << EOF
# API URLs (CDK 배포 후 업데이트 필요)
REACT_APP_API_URL=
REACT_APP_WS_URL=

# AWS Cognito (CDK 배포 후 업데이트 필요)
REACT_APP_USER_POOL_ID=
REACT_APP_USER_POOL_CLIENT_ID=

# 인증 설정
REACT_APP_SKIP_AUTH=false

# 프로젝트 정보
REACT_APP_PROJECT_NAME=$PROJECT_DISPLAY_NAME
REACT_APP_PROJECT_DESCRIPTION=$PROJECT_DISPLAY_NAME AI Service
EOF

# 프롬프트 디렉토리 생성
echo "📁 프롬프트 디렉토리 구조 생성 중..."
mkdir -p prompts/projects/$PROJECT_NAME/templates

# 프로젝트 설정 파일 생성
cat > prompts/projects/$PROJECT_NAME/config.json << EOF
{
  "project_name": "$PROJECT_NAME",
  "display_name": "$PROJECT_DISPLAY_NAME",
  "description": "$PROJECT_DISPLAY_NAME AI Service",
  "agents": [
    {
      "type": "default",
      "name": "기본 에이전트",
      "description": "기본 AI 에이전트",
      "prompt_file": "templates/default.txt"
    }
  ]
}
EOF

# 기본 프롬프트 템플릿 생성
cat > prompts/projects/$PROJECT_NAME/templates/default.txt << 'EOF'
You are a helpful AI assistant for $PROJECT_DISPLAY_NAME.

User Input: {user_input}

Please provide a helpful response.
EOF

# Git 초기화 (선택사항)
read -p "Git 저장소를 초기화하시겠습니까? (y/n): " INIT_GIT
if [ "$INIT_GIT" = "y" ]; then
    echo "📦 Git 저장소 초기화 중..."
    rm -rf .git
    git init
    git add .
    git commit -m "Initial commit for $PROJECT_NAME"
fi

echo ""
echo "✅ 프로젝트 설정 완료!"
echo "========================="
echo ""
echo "다음 단계:"
echo "1. CDK 의존성 설치:"
echo "   cd cdk && pip install -r requirements.txt"
echo ""
echo "2. 프론트엔드 의존성 설치:"
echo "   cd frontend && npm install"
echo ""
echo "3. CDK Bootstrap (최초 1회):"
echo "   cd cdk && cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION"
echo ""
echo "4. 백엔드 배포:"
echo "   cd cdk && cdk deploy ${STACK_PREFIX}StackDev"
echo ""
echo "5. frontend/.env 파일에 CDK 출력값 업데이트"
echo ""
echo "6. 프론트엔드 배포:"
echo "   cd cdk && cdk deploy ${STACK_PREFIX}FrontendStackDev"