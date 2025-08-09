# 🔐 GitHub Secrets 설정 가이드

## 📋 필수 설정 사항

GitHub Actions가 AWS에 배포하려면 다음 Secrets를 설정해야 합니다.

## 🚀 설정 방법

### 1. GitHub 리포지토리 접속
https://github.com/sedaily/sedaily-ainexus-title-ver1

### 2. Settings → Secrets and variables → Actions

### 3. 다음 Secrets 추가 (New repository secret)

## 🔑 필수 Secrets

### 1️⃣ AWS_ACCESS_KEY_ID
```
AWS IAM 사용자의 Access Key ID
예시: AKIAIOSFODNN7EXAMPLE
```

### 2️⃣ AWS_SECRET_ACCESS_KEY
```
AWS IAM 사용자의 Secret Access Key
예시: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### 3️⃣ AWS_ACCOUNT_ID
```
AWS 계정 ID (12자리 숫자)
현재 계정: 887078546492
```

## 📝 AWS IAM 사용자 생성 방법

### AWS Console에서:

1. **IAM → Users → Create user**
2. **User name**: `github-actions-deployer`
3. **Permissions**: 다음 정책 연결
   - AdministratorAccess (또는 필요한 최소 권한)

### 또는 AWS CLI로:

```bash
# IAM 사용자 생성
aws iam create-user --user-name github-actions-deployer

# Access Key 생성
aws iam create-access-key --user-name github-actions-deployer

# 정책 연결 (AdministratorAccess 예시)
aws iam attach-user-policy \
  --user-name github-actions-deployer \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

## ✅ 설정 확인

모든 Secrets가 설정되면:
1. Actions 탭에서 워크플로우 확인
2. "Run workflow" 버튼으로 수동 실행 가능
3. 또는 코드 push 시 자동 실행

## 🔍 현재 AWS 리소스 정보

```yaml
AWS_REGION: ap-northeast-2
ACCOUNT_ID: 887078546492
STACK_NAMES:
  - Production: JournalismFaithfulStack
  - Development: JournalismFaithfulStackDev
```

## ⚠️ 보안 주의사항

- Secrets는 절대 코드에 하드코딩하지 마세요
- Access Key는 정기적으로 교체하세요
- 최소 권한 원칙을 적용하세요
- 사용하지 않는 Access Key는 즉시 삭제하세요

## 📞 문의

설정 중 문제가 있으시면:
- GitHub Issues 생성
- 개발팀 문의