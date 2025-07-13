#!/bin/bash

# AI팀 계정 일괄 생성 스크립트
# 사용법: ./create_ai_users.sh USER_POOL_ID

if [ -z "$1" ]; then
    echo "사용법: ./create_ai_users.sh USER_POOL_ID"
    echo "예시: ./create_ai_users.sh ap-northeast-2_XXXXXXXXX"
    exit 1
fi

USER_POOL_ID="$1"
PASSWORD="sedaily2024!"
REGION="ap-northeast-2"

# AI팀 계정 목록
AI_USERS=(
    "ai@sedaily.com"
    "ai01@sedaily.com"
    "ai02@sedaily.com"
    "ai03@sedaily.com"
    "ai04@sedaily.com"
    "ai05@sedaily.com"
)

echo "🚀 AI팀 계정 생성 시작..."
echo "User Pool ID: $USER_POOL_ID"
echo "Region: $REGION"
echo "비밀번호: $PASSWORD"
echo ""

for EMAIL in "${AI_USERS[@]}"; do
    echo "📧 $EMAIL 계정 생성 중..."
    
    # 사용자 생성
    if aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$EMAIL" \
        --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
        --temporary-password "$PASSWORD" \
        --message-action SUPPRESS \
        --region "$REGION" \
        --no-cli-pager 2>/dev/null; then
        
        # 비밀번호 영구 설정
        if aws cognito-idp admin-set-user-password \
            --user-pool-id "$USER_POOL_ID" \
            --username "$EMAIL" \
            --password "$PASSWORD" \
            --permanent \
            --region "$REGION" \
            --no-cli-pager 2>/dev/null; then
            
            echo "✅ $EMAIL 계정 생성 완료!"
        else
            echo "⚠️  $EMAIL 비밀번호 설정 실패"
        fi
    else
        echo "❌ $EMAIL 계정 생성 실패 (이미 존재할 수 있음)"
    fi
    echo ""
done

echo "🎉 작업 완료!"
echo ""
echo "📋 생성된 계정 목록:"
aws cognito-idp list-users --user-pool-id "$USER_POOL_ID" --region "$REGION" --query "Users[].Attributes[?Name=='email'].Value" --output table