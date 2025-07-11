# 🚀 TITLE-NOMICS: AWS Bedrock DIY 제목 생성기

AWS Bedrock을 활용한 서울경제신문 스타일의 AI 제목 생성 시스템입니다.

## 📋 프로젝트 개요

이 프로젝트는 기존 Streamlit 기반의 제목 생성 시스템을 AWS Bedrock + 전체 AWS 생태계로 확장한 프로덕션 레벨의 애플리케이션입니다.

### 주요 특징

- **React 프론트엔드**: 실제 사용자가 사용할 수 있는 웹 애플리케이션
- **AWS Bedrock**: Claude 3.5 Sonnet을 활용한 제목 생성
- **벡터 검색**: OpenSearch를 통한 프롬프트 임베딩 및 검색
- **자동 색인**: S3 업로드 시 자동 임베딩 생성 및 색인
- **확장 가능한 아키텍처**: 서버리스 기반으로 자동 확장

### 아키텍처

```
프론트엔드(React) → API Gateway → Lambda → Bedrock
                                    ↓
                    S3 → Lambda → OpenSearch
                                    ↓
                              DynamoDB
```

## 🛠️ 기술 스택

### Backend

- **AWS CDK**: 인프라 코드 관리
- **AWS Lambda**: 서버리스 컴퓨팅
- **AWS Bedrock**: Claude 3.5 Sonnet 모델
- **Amazon OpenSearch**: 벡터 검색 엔진
- **Amazon DynamoDB**: NoSQL 데이터베이스
- **Amazon S3**: 파일 저장소
- **API Gateway**: REST API 관리

### Frontend

- **React**: UI 라이브러리
- **Tailwind CSS**: 스타일링
- **Axios**: HTTP 클라이언트
- **React Router**: 라우팅
- **React Hot Toast**: 알림 시스템

## 📁 프로젝트 구조

```
bedrock-diy-title-generator/
├── cdk/                          # AWS CDK 인프라 코드
│   ├── app.py                   # CDK 메인 앱
│   ├── bedrock_stack.py         # CDK 스택 정의
│   └── requirements.txt         # Python 의존성
├── lambda/                       # Lambda 함수들
│   ├── index_prompt/            # 프롬프트 색인 Lambda
│   │   ├── index_prompt.py
│   │   └── requirements.txt
│   ├── generate/                # 제목 생성 Lambda
│   │   ├── generate.py
│   │   └── requirements.txt
│   └── project/                 # 프로젝트 관리 Lambda
│       ├── project.py
│       └── requirements.txt
├── frontend/                     # React 프론트엔드
│   ├── public/
│   ├── src/
│   │   ├── components/          # React 컴포넌트
│   │   ├── services/           # API 서비스
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── tailwind.config.js
├── prompts/                     # 프롬프트 파일들 (기존)
└── README.md
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- **AWS CLI** 설치 및 구성
- **Node.js** 16+ 설치
- **Python** 3.11+ 설치
- **AWS CDK** 설치
- **AWS 계정** 및 Bedrock 모델 액세스 권한

### 2. AWS 설정

```bash
# AWS CLI 구성
aws configure

# Bedrock 모델 액세스 활성화 (AWS 콘솔에서)
# - Claude 3.5 Sonnet 모델 활성화
# - Titan Embeddings 모델 활성화
```

### 3. 인프라 배포

```bash
# CDK 의존성 설치
cd cdk
pip install -r requirements.txt

# CDK 부트스트랩 (최초 1회)
cdk bootstrap

# 스택 배포
cdk deploy
```

배포가 완료되면 다음과 같은 출력값을 얻을 수 있습니다:

- **ApiGatewayUrl**: API Gateway 엔드포인트
- **PromptBucketName**: 프롬프트 S3 버킷 이름
- **OpenSearchEndpoint**: OpenSearch 도메인 엔드포인트

### 4. 프론트엔드 설정

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# 의존성 설치
npm install

# 환경 변수 설정
echo "REACT_APP_API_URL=https://your-api-gateway-url.amazonaws.com/prod" > .env

# 개발 서버 실행
npm start
```

## 📝 사용 방법

### 1. 프로젝트 생성

1. 웹 애플리케이션 접속
2. "새 프로젝트" 버튼 클릭
3. 프로젝트 이름 및 설명 입력
4. 프로젝트 생성 완료

### 2. 프롬프트 설정

1. 생성된 프로젝트 진입
2. "프롬프트 설정" 탭 선택
3. 11개 카테고리별 프롬프트 파일 업로드:
   - ✅ **필수**: title_type_guidelines, stylebook_guidelines, workflow 등
   - ⚪ **선택**: seo_optimization 등
4. 업로드 완료 후 자동 색인 대기

### 3. 제목 생성

1. "제목 생성" 탭 선택
2. 기사 원문 입력 (최소 100자)
3. "제목 생성" 버튼 클릭
4. AI 분석 결과 및 다양한 제목 옵션 확인
5. 최종 추천 제목 선택 및 복사

### 4. 결과 확인

- 기사 분석 결과
- 카테고리별 제목 (직설적, 질문형, 임팩트)
- 최종 추천 제목 및 선정 이유
- 사용 통계 (토큰 수, 실행 시간)

## 🔧 설정 및 커스터마이징

### 환경 변수

#### 프론트엔드 (.env)

```
REACT_APP_API_URL=https://your-api-gateway-url.amazonaws.com/prod
```

#### Lambda 함수 (CDK에서 자동 설정)

```
OPENSEARCH_ENDPOINT=your-opensearch-endpoint
PROJECT_TABLE=bedrock-diy-projects
PROMPT_META_TABLE=bedrock-diy-prompt-meta
CONVERSATION_TABLE=bedrock-diy-conversations
REGION=us-east-1
```

### 프롬프트 카테고리

현재 지원하는 11개 카테고리:

1. **title_type_guidelines** (필수): 제목 유형 가이드라인
2. **stylebook_guidelines** (필수): 스타일북 가이드라인
3. **workflow** (필수): 6단계 워크플로우
4. **audience_optimization** (필수): 독자 최적화
5. **seo_optimization** (선택): SEO 최적화
6. **digital_elements_guidelines** (필수): 디지털 요소 가이드라인
7. **quality_assessment** (필수): 품질 평가
8. **uncertainty_handling** (필수): 불확실성 처리
9. **output_format** (필수): 출력 형식
10. **description** (필수): 프로젝트 설명
11. **knowledge** (필수): 핵심 지식

## 💰 비용 최적화

### 예상 비용 (월간)

- **Lambda**: 요청 기반 과금 (~$5-20)
- **Bedrock**: 토큰 기반 과금 (~$10-50)
- **OpenSearch**: t3.small.search (~$25)
- **DynamoDB**: 요청 기반 과금 (~$1-5)
- **S3**: 저장 용량 기반 (~$1-5)

### 비용 절약 팁

1. **S3 Lifecycle**: 90일 후 GLACIER 전환
2. **Lambda 메모리**: 필요에 따라 조정
3. **OpenSearch**: 개발 환경에서는 더 작은 인스턴스 사용
4. **CloudWatch 모니터링**: 사용량 기반 알람 설정

## 🔍 모니터링 및 알람

### CloudWatch 알람

- Lambda 함수 오류율 (5회 이상)
- Lambda 함수 지연 시간 (30초 이상)
- OpenSearch 메모리 사용률 (80% 이상)

### 로그 확인

```bash
# Lambda 로그 확인
aws logs tail /aws/lambda/bedrock-diy-index-prompt --follow
aws logs tail /aws/lambda/bedrock-diy-generate --follow
aws logs tail /aws/lambda/bedrock-diy-project --follow
```

## 🛡️ 보안 고려사항

### IAM 권한

- 최소 권한 원칙 적용
- 리소스별 세분화된 권한 설정
- 프로덕션 환경에서는 더 엄격한 권한 적용

### 네트워크 보안

- API Gateway CORS 설정
- OpenSearch 접근 제한
- VPC 내부 배치 (프로덕션 환경)

### 데이터 보호

- S3 버킷 암호화
- DynamoDB 암호화
- 민감한 정보 Guardrail 적용

## 🚨 문제 해결

### 자주 발생하는 문제

1. **Bedrock 모델 액세스 오류**

   ```
   해결: AWS 콘솔에서 Bedrock 모델 액세스 권한 활성화
   ```

2. **OpenSearch 접근 오류**

   ```
   해결: IAM 정책 및 OpenSearch 접근 정책 확인
   ```

3. **Lambda 타임아웃**

   ```
   해결: 메모리 크기 증가 또는 타임아웃 시간 연장
   ```

4. **프롬프트 색인 실패**
   ```
   해결: S3 이벤트 트리거 및 Lambda 함수 로그 확인
   ```

### 디버깅 팁

1. **CloudWatch 로그 확인**
2. **API Gateway 테스트 콘솔 사용**
3. **Lambda 함수 직접 테스트**
4. **DynamoDB 테이블 데이터 확인**

## 📚 참고 자료

- [AWS Bedrock 문서](https://docs.aws.amazon.com/bedrock/)
- [AWS CDK 문서](https://docs.aws.amazon.com/cdk/)
- [Claude 3.5 Sonnet 가이드](https://docs.anthropic.com/claude/docs)
- [OpenSearch 문서](https://docs.aws.amazon.com/opensearch-service/)

## 🤝 기여하기

1. Fork 프로젝트
2. Feature 브랜치 생성
3. 변경사항 커밋
4. Pull Request 제출

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다.

---

**🎯 목표 달성!** 이제 "설정 마쳤는데 아무 응답이 안 와요…" 같은 DM은 덜 올 거예요! 😄

터미널을 열고 `cdk bootstrap`을 실행하고, 멋진 제목 생성기를 만들어보세요! 🚀
