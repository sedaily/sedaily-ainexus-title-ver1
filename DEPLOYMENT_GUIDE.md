# 🚀 AI 제목 생성기 - 내부 직원용 배포 가이드

## 📌 주요 변경사항

### 1. Cognito 비밀번호 정책 완화
- **변경 전**: 대문자, 소문자, 숫자, 특수문자 모두 필수
- **변경 후**: 숫자, 특수문자만 필수 (최소 8자)
- **예시 비밀번호**: `sedaily2024!`

### 2. 회원가입 비활성화
- 일반 사용자 회원가입 기능 제거
- 관리자만 AWS CLI를 통해 계정 생성 가능

## 🔧 배포 절차

### 1단계: CDK 재배포

```bash
# CDK 디렉토리로 이동
cd cdk

# 변경사항 배포 (승인 없이 자동 배포)
cdk deploy --require-approval never
```

### 2단계: 프론트엔드 배포

```bash
# 프론트엔드 디렉토리로 이동
cd ../frontend

# 빌드
npm run build

# S3에 배포 (CloudFront 캐시 무효화 포함)
aws s3 sync build/ s3://your-frontend-bucket --delete
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

## 👥 직원 계정 생성

### 환경 변수 설정

```bash
# Cognito User Pool ID (CDK 배포 후 출력값 확인)
USER_POOL_ID="ap-northeast-2_XXXXXXXXX"

# 임시 비밀번호 (숫자+특수문자 포함)
TEMP_PASSWORD="sedaily2024!"
```

### 계정 생성 명령어 (한 줄 복사용)

```bash
# AI팀 계정 생성
aws cognito-idp admin-create-user --user-pool-id "$USER_POOL_ID" --username "ai@sedaily.com" --user-attributes Name=email,Value="ai@sedaily.com" Name=email_verified,Value=true --temporary-password "$TEMP_PASSWORD" --message-action SUPPRESS --no-cli-pager && aws cognito-idp admin-set-user-password --user-pool-id "$USER_POOL_ID" --username "ai@sedaily.com" --password "$TEMP_PASSWORD" --permanent --no-cli-pager

# 편집팀 계정 생성
aws cognito-idp admin-create-user --user-pool-id "$USER_POOL_ID" --username "editor@sedaily.com" --user-attributes Name=email,Value="editor@sedaily.com" Name=email_verified,Value=true --temporary-password "$TEMP_PASSWORD" --message-action SUPPRESS --no-cli-pager && aws cognito-idp admin-set-user-password --user-pool-id "$USER_POOL_ID" --username "editor@sedaily.com" --password "$TEMP_PASSWORD" --permanent --no-cli-pager

# 디지털팀 계정 생성
aws cognito-idp admin-create-user --user-pool-id "$USER_POOL_ID" --username "digital@sedaily.com" --user-attributes Name=email,Value="digital@sedaily.com" Name=email_verified,Value=true --temporary-password "$TEMP_PASSWORD" --message-action SUPPRESS --no-cli-pager && aws cognito-idp admin-set-user-password --user-pool-id "$USER_POOL_ID" --username "digital@sedaily.com" --password "$TEMP_PASSWORD" --permanent --no-cli-pager
```

### 대량 계정 생성 스크립트

```bash
#!/bin/bash
# create_users.sh

USER_POOL_ID="ap-northeast-2_XXXXXXXXX"
TEMP_PASSWORD="sedaily2024!"

# 사용자 목록
USERS=(
    "ai@sedaily.com"
    "editor@sedaily.com"
    "digital@sedaily.com"
    "reporter1@sedaily.com"
    "reporter2@sedaily.com"
)

# 각 사용자 생성
for EMAIL in "${USERS[@]}"; do
    echo "Creating user: $EMAIL"
    
    # 사용자 생성
    aws cognito-idp admin-create-user \
        --user-pool-id "$USER_POOL_ID" \
        --username "$EMAIL" \
        --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
        --temporary-password "$TEMP_PASSWORD" \
        --message-action SUPPRESS \
        --no-cli-pager
    
    # 비밀번호 영구 설정
    aws cognito-idp admin-set-user-password \
        --user-pool-id "$USER_POOL_ID" \
        --username "$EMAIL" \
        --password "$TEMP_PASSWORD" \
        --permanent \
        --no-cli-pager
    
    echo "✅ $EMAIL 계정 생성 완료"
    echo ""
done
```

## 🔐 보안 권장사항

1. **비밀번호 관리**
   - 초기 비밀번호는 첫 로그인 후 변경 권장
   - 팀별로 다른 비밀번호 사용 고려

2. **접근 제어**
   - VPN 환경에서만 접근 가능하도록 설정
   - CloudFront에 IP 화이트리스트 적용

3. **모니터링**
   - CloudWatch에서 로그인 실패 알람 설정
   - 비정상적인 접근 패턴 모니터링

## ❓ 문제 해결

### 로그인 실패 시
```bash
# 사용자 상태 확인
aws cognito-idp admin-get-user --user-pool-id "$USER_POOL_ID" --username "email@sedaily.com"

# 비밀번호 재설정
aws cognito-idp admin-set-user-password --user-pool-id "$USER_POOL_ID" --username "email@sedaily.com" --password "newpassword2024!" --permanent
```

### 계정 비활성화
```bash
# 계정 비활성화
aws cognito-idp admin-disable-user --user-pool-id "$USER_POOL_ID" --username "email@sedaily.com"

# 계정 활성화
aws cognito-idp admin-enable-user --user-pool-id "$USER_POOL_ID" --username "email@sedaily.com"
```

## 📞 지원 연락처

- **기술 문의**: AI개발팀 (내선 1234)
- **계정 문의**: 시스템관리팀 (내선 5678)
- **긴급 지원**: 010-XXXX-XXXX

---

**마지막 업데이트**: 2024-01-13
**작성자**: AI개발팀