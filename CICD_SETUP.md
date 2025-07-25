# 🚀 CI/CD 자동 배포 설정 가이드

## 📋 **개요**

이 가이드는 **Title Generator** 프로젝트의 **GitHub Actions CI/CD** 자동 배포를 설정하는 방법을 안내합니다.

### **배포 플로우**

```
GitHub Push → 테스트 → CDK 배포 (백엔드) → S3 배포 (프론트엔드) → 헬스체크
```

### **환경 분리**

- **main** 브랜치 → **프로덕션** 환경
- **develop** 브랜치 → **개발** 환경
- **로컬** → 수동 배포 (기존 방식)

---

## 🔧 **1단계: GitHub Secrets 설정**

### **필수 Secrets**

GitHub 저장소에서 `Settings → Secrets and variables → Actions → New repository secret`에서 다음을 추가:

```bash
# AWS 자격 증명 (필수)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# CloudFront 배포 ID (선택사항)
CLOUDFRONT_DISTRIBUTION_ID_PROD=E1A2B3C4D5F6G7
CLOUDFRONT_DISTRIBUTION_ID_DEV=E7G6F5D4C3B2A1
```

### **AWS 자격 증명 얻기**

1. **AWS Console → IAM → Users → [사용자 이름] → Security credentials**
2. **"Create access key" 클릭**
3. **"Command Line Interface (CLI)" 선택**
4. **Access Key ID와 Secret Access Key 복사**

### **필요한 IAM 권한**

CI/CD 사용자에게 다음 권한 필요:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "lambda:*",
        "apigateway:*",
        "iam:*",
        "dynamodb:*",
        "cognito-idp:*",
        "cloudfront:*",
        "logs:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 🌳 **2단계: 브랜치 설정**

### **개발 브랜치 생성**

```bash
# 현재 main 브랜치에서 develop 브랜치 생성
git checkout -b develop
git push -u origin develop
```

### **브랜치 보호 규칙 설정**

**GitHub → Settings → Branches → Add rule**:

#### **main 브랜치 (프로덕션)**

- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass before merging
- ✅ Include administrators

#### **develop 브랜치 (개발)**

- ✅ Require status checks to pass before merging

---

## 🏗️ **3단계: S3 버킷 미리 생성 (선택사항)**

GitHub Actions가 자동으로 생성하지만, 미리 생성하고 싶다면:

```bash
# AWS CLI로 버킷 생성
aws s3 mb s3://title-generator-frontend-prod --region us-east-1
aws s3 mb s3://title-generator-frontend-dev --region us-east-1

# 버킷 정책 설정 (공개 액세스 차단)
aws s3api put-public-access-block \
  --bucket title-generator-frontend-prod \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

---

## 🚀 **4단계: 첫 배포 테스트**

### **개발 환경 배포 테스트**

```bash
# develop 브랜치에 푸시
git checkout develop
git add .
git commit -m "🚀 CI/CD: 개발 환경 첫 배포 테스트"
git push origin develop
```

### **프로덕션 배포**

```bash
# develop → main 머지
git checkout main
git merge develop
git push origin main
```

### **배포 상태 확인**

1. **GitHub → Actions 탭**에서 워크플로우 진행 상황 확인
2. **AWS Console**에서 스택 생성 확인:
   - `BedrockDiyTitleGeneratorStackDev` / `BedrockDiyTitleGeneratorStackProd`
   - `ConversationStackDev` / `ConversationStackProd`
   - `TitleGeneratorFrontendStackDev` / `TitleGeneratorFrontendStackProd`

---

## 📊 **5단계: 배포 완료 확인**

### **백엔드 API 테스트**

```bash
# 개발 환경
curl https://[dev-api-url]/conversations?limit=1

# 프로덕션 환경
curl https://[prod-api-url]/conversations?limit=1
```

### **프론트엔드 접속**

1. **S3 버킷 확인**:

   ```bash
   aws s3 ls s3://title-generator-frontend-prod
   aws s3 ls s3://title-generator-frontend-dev
   ```

2. **CloudFront URL 접속** (설정한 경우)

---

## 🔧 **6단계: 환경별 설정 커스터마이징**

### **환경 변수 추가**

`.github/workflows/deploy.yml`에서 환경별 변수 추가:

```yaml
- name: 🔧 Setup environment variables
  run: |
    # 커스텀 환경별 설정 추가
    if [ "${{ github.ref }}" = "refs/heads/main" ]; then
      CUSTOM_VAR="production-value"
    else
      CUSTOM_VAR="development-value"
    fi

    echo "REACT_APP_CUSTOM_VAR=$CUSTOM_VAR" >> .env.production
```

### **도메인 연결 (선택사항)**

1. **Route 53에서 도메인 구매/설정**
2. **Certificate Manager에서 SSL 인증서 발급**
3. **CloudFront 배포에 커스텀 도메인 연결**

---

## 🚨 **문제 해결 가이드**

### **자주 발생하는 오류**

#### **1. AWS 권한 오류**

```
Error: User: arn:aws:iam::123456789012:user/github-actions is not authorized to perform: cloudformation:CreateStack
```

**해결**: IAM 사용자에게 필요한 권한 추가

#### **2. S3 버킷 이름 충돌**

```
Error: Bucket name already exists
```

**해결**: `frontend_stack.py`에서 버킷 이름 수정

#### **3. CDK 버전 불일치**

```
Error: CDK version mismatch
```

**해결**: 로컬과 CI/CD의 CDK 버전 통일

#### **4. 테스트 실패**

```
Error: Test suite failed to run
```

**해결**: `frontend/src/App.test.js` 수정 또는 테스트 건너뛰기

### **디버깅 방법**

1. **GitHub Actions 로그 확인**
2. **AWS CloudFormation 이벤트 확인**
3. **CloudWatch 로그 확인**

---

## 📈 **성능 최적화 팁**

### **빌드 속도 개선**

```yaml
# package.json 캐싱 활용
- uses: actions/setup-node@v4
  with:
    cache: "npm"
    cache-dependency-path: frontend/package-lock.json
```

### **배포 시간 단축**

```yaml
# 병렬 배포 (리스크 있음)
strategy:
  matrix:
    stack: [backend, frontend]
```

### **비용 절약**

- **개발 환경**: 자동 삭제 정책 적용
- **프로덕션**: 수동 승인 단계 추가
- **S3**: 라이프사이클 정책 설정

---

## 🎯 **결론**

✅ **CI/CD 설정 완료!**

이제 다음과 같이 자동 배포됩니다:

1. **develop 브랜치 푸시** → **개발 환경 자동 배포**
2. **main 브랜치 머지** → **프로덕션 환경 자동 배포**
3. **Pull Request** → **테스트만 실행**

### **다음 단계**

- 🔔 **Slack/Discord 알림** 설정
- 📊 **모니터링** 대시보드 구축
- 🔄 **자동 롤백** 기능 추가
- 🧪 **E2E 테스트** 자동화

---

## 📞 **지원**

문제가 발생하면:

1. **GitHub Actions 로그** 확인
2. **AWS Console** 에러 메시지 확인
3. **이 문서의 문제 해결 섹션** 참조

**Happy Deploying! 🚀**
