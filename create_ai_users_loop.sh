#!/usr/bin/env bash
USER_POOL_ID=ap-northeast-2_4XNXI86AJ
TEMP_PASSWORD=Sedaily2024!
EMAILS=("ai@sedaily.com" "ai01@sedaily.com" "ai02@sedaily.com" "ai03@sedaily.com" "ai04@sedaily.com" "ai05@sedaily.com" "ai06@sedaily.com")

for email in "${EMAILS[@]}"; do
  echo "---"
  echo "👤 $email 계정 처리 중..."
  aws cognito-idp admin-create-user \
    --user-pool-id "$USER_POOL_ID" \
    --username "$email" \
    --user-attributes Name=email,Value="$email" Name=email_verified,Value=true \
    --temporary-password "$TEMP_PASSWORD" \
    --message-action SUPPRESS \
    --no-cli-pager \
  || echo "🔹 계정이 이미 존재하여, 비밀번호 설정으로 넘어갑니다."

  aws cognito-idp admin-set-user-password \
    --user-pool-id "$USER_POOL_ID" \
    --username "$email" \
    --password "$TEMP_PASSWORD" \
    --permanent \
    --no-cli-pager

  echo "✅ $email 계정 비밀번호 설정 완료"
done

echo ""
echo "🎉 모든 계정 작업이 완료되었습니다!"
echo "--- 최종 계정 목록 ---"
aws cognito-idp list-users \
  --user-pool-id "$USER_POOL_ID" \
  --query "Users[*].Username" \
  --output table
