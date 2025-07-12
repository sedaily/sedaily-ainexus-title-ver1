# TITLE-NOMICS 배포 가이드

## 개요

TITLE-NOMICS는 GitHub 기반 CI/CD와 AWS 서버리스 아키텍처를 사용하는 현대적인 웹 애플리케이션입니다.

### 아키텍처

```
GitHub → GitHub Actions → AWS CDK →
├── 백엔드: Lambda + API Gateway + DynamoDB + Bedrock
└── 프론트엔드: S3 + CloudFront
```

## 배포 방법

### 방법 1: 자동 배포 (GitHub Actions) - 추천

1. **GitHub Repository 설정**

   ```bash
   git add .
   git commit -m "Add CI/CD pipeline"
   git push origin main
   ```

2. **GitHub Secrets 설정**

   - Repository Settings → Secrets and variables → Actions
   - 다음 시크릿 추가:
     - `AWS_ACCESS_KEY_ID`: AWS 액세스 키
     - `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키

3. **자동 배포 실행**
   - `main` 브랜치에 푸시하면 자동으로 배포됨
   - Actions 탭에서 배포 진행상황 확인

### 방법 2: 수동 배포 (로컬)

1. **전체 시스템 배포**

   ```bash
   chmod +x scripts/deploy-all.sh
   ./scripts/deploy-all.sh
   ```

2. **백엔드만 배포**

   ```bash
   cd cdk
   cdk deploy BedrockDiyAuthStack
   ```

3. **프론트엔드만 배포**
   ```bash
   chmod +x scripts/deploy-frontend.sh
   ./scripts/deploy-frontend.sh <API_URL>
   ```

## 사전 요구사항

### 필수 도구

- AWS CLI (구성 완료)
- Node.js 18+
- Python 3.11+
- AWS CDK
- jq (JSON 파서)

### AWS 권한

- Bedrock 모델 액세스 권한
- CloudFormation 스택 생성 권한
- Lambda, API Gateway, S3, CloudFront 권한

### Bedrock 모델 활성화

AWS 콘솔에서 다음 모델들을 활성화해야 합니다:

- Claude 3.5 Sonnet v2 (제목 생성)
- Claude 3.5 Sonnet (채팅)
- Claude 3 Haiku (요약)
- Titan Embeddings (벡터 검색)

## 배포 과정

### 1단계: 백엔드 인프라

- Lambda 함수들 (generate, langchain_router, project, auth, save_prompt)
- API Gateway + Cognito 인증
- DynamoDB 테이블들
- S3 버킷 (프롬프트 저장)
- Bedrock Agent 및 Guardrail

### 2단계: 프론트엔드 빌드

- React 애플리케이션 빌드
- 환경 변수 설정 (API URL 자동 연결)
- 코드 품질 검사 및 테스트

### 3단계: 프론트엔드 배포

- S3 정적 호스팅
- CloudFront CDN 배포
- 캐시 무효화

## 배포 후 확인사항

### 1. 백엔드 API 테스트

```bash
# API 상태 확인
curl https://your-api-url/auth/signin -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'
```

### 2. 프론트엔드 접속

- CloudFront URL로 접속
- 회원가입/로그인 테스트
- 프로젝트 생성 테스트

### 3. 기능 테스트

- 프롬프트 카드 업로드
- 제목 생성 기능
- AI 채팅 기능

## 비용 최적화

### 예상 월 비용

- **Lambda**: $5-20 (요청 기반)
- **Bedrock**: $10-50 (토큰 기반)
- **S3**: $1-5 (저장 용량)
- **CloudFront**: $1-10 (트래픽)
- **DynamoDB**: $1-5 (요청 기반)
- **총합**: $20-90 (사용량에 따라)

### 비용 절약 팁

1. **S3 Lifecycle**: 90일 후 GLACIER 전환
2. **CloudFront**: 최소 Price Class 사용
3. **Lambda**: 메모리 최적화
4. **DynamoDB**: On-Demand 모드 사용
5. **미사용 시**: `cdk destroy --all`로 완전 삭제

## 모니터링

### CloudWatch 대시보드

- Lambda 함수 메트릭
- API Gateway 메트릭
- Bedrock 사용량
- 비용 알람

### 로그 확인

```bash
# Lambda 로그
aws logs tail /aws/lambda/bedrock-diy-generate-auth --follow

# API Gateway 로그
aws logs tail /aws/apigateway/bedrock-diy-api --follow
```

### 알람 설정

- Lambda 오류율 > 5%
- API Gateway 지연시간 > 30초
- 월 비용 > $100

## 문제 해결

### 자주 발생하는 문제

1. **Bedrock 모델 액세스 오류**

   ```
   해결: AWS 콘솔에서 Bedrock 모델 액세스 권한 활성화
   ```

2. **CloudFront 배포 지연**

   ```
   해결: 최대 15분 대기, 캐시 무효화 확인
   ```

3. **Lambda 타임아웃**

   ```
   해결: 메모리 크기 증가 또는 타임아웃 연장
   ```

4. **CORS 오류**
   ```
   해결: API Gateway CORS 설정 확인
   ```

### 디버깅 명령어

```bash
# CDK 스택 상태 확인
cdk list
cdk diff

# CloudFormation 스택 확인
aws cloudformation describe-stacks --stack-name BedrockDiyAuthStack

# Lambda 함수 테스트
aws lambda invoke --function-name bedrock-diy-generate-auth \
  --payload '{"test": true}' response.json
```

## 업데이트 및 관리

### 코드 업데이트

```bash
# GitHub Actions 사용 시
git add .
git commit -m "Update feature"
git push origin main

# 수동 배포 시
./scripts/deploy-all.sh
```

### 백엔드만 업데이트

```bash
cd cdk
cdk deploy BedrockDiyAuthStack
```

### 프론트엔드만 업데이트

```bash
cd frontend
npm run build
cd ../cdk
cdk deploy FrontendStack
```

### 롤백

```bash
# 이전 버전으로 롤백
git revert HEAD
git push origin main

# 또는 특정 커밋으로
git reset --hard <commit-hash>
git push --force origin main
```

## 보안 고려사항

### IAM 권한

- 최소 권한 원칙 적용
- 리소스별 세분화된 권한
- 정기적인 권한 검토

### 네트워크 보안

- API Gateway CORS 설정
- CloudFront HTTPS 강제
- Cognito 인증 필수

### 데이터 보호

- S3 버킷 암호화
- DynamoDB 암호화
- Bedrock Guardrail 적용

## 확장성

### 트래픽 증가 대응

- Lambda 동시 실행 제한 조정
- CloudFront 캐싱 정책 최적화
- DynamoDB Auto Scaling 활성화

### 기능 확장

- 새로운 Lambda 함수 추가
- API Gateway 경로 확장
- 추가 Bedrock 모델 연동

## 지원 및 문의

### 문제 신고

- GitHub Issues 사용
- 로그 파일 첨부
- 재현 단계 상세 기술

### 개발 환경 설정

```bash
# 로컬 개발 서버 실행
cd frontend
npm start

# 백엔드 로컬 테스트
cd lambda/generate
python generate.py
```

이 가이드를 따라 안정적이고 확장 가능한 TITLE-NOMICS 시스템을 배포하고 관리할 수 있습니다.
