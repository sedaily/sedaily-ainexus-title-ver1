# TITLE-NOMICS 성능 최적화 및 CI/CD 가이드

## 개요

TITLE-NOMICS 시스템의 성능 최적화, 모니터링 강화, 그리고 GitHub Actions 기반 CI/CD 파이프라인 구축 가이드입니다.

## 🚀 주요 개선사항

### 1. 성능 최적화

- **Lambda 메모리 최적화**: 메모리 부족 문제 해결
- **타임아웃 연장**: 복잡한 프롬프트 체이닝 처리 시간 확보
- **동시 실행 제한**: 과도한 동시 실행으로 인한 비용 증가 방지
- **Provisioned Concurrency**: 콜드 스타트 문제 해결

### 2. 모니터링 강화

- **실시간 알람**: Lambda 오류율, 지연시간, 메모리 사용률 모니터링
- **CloudWatch 대시보드**: 통합 성능 모니터링
- **비용 알람**: 월 예산 초과 시 자동 알림
- **WAF 보안**: Rate Limiting 및 악성 트래픽 차단

### 3. CI/CD 자동화

- **GitHub Actions**: 코드 푸시 시 자동 배포
- **S3 + CloudFront**: 프론트엔드 정적 호스팅
- **API 프록시**: CloudFront를 통한 API 연동
- **캐시 무효화**: 배포 후 자동 캐시 갱신

## 📋 배포 단계

### 1단계: 기존 백엔드 스택 배포

```bash
cd cdk
cdk deploy BedrockDiyAuthStack --require-approval never
```

### 2단계: 성능 최적화 스택 배포

```bash
cdk deploy PerformanceOptimizationStack --require-approval never
```

### 3단계: CI/CD 스택 배포

```bash
cdk deploy CICDStack --require-approval never
```

## 🔧 성능 최적화 상세

### Lambda 함수별 최적화

| 함수명               | 기존 설정   | 최적화 설정  | 개선 효과                            |
| -------------------- | ----------- | ------------ | ------------------------------------ |
| **langchain_router** | 2048MB, 5분 | 3008MB, 10분 | 메모리 부족 해결, 복잡한 체이닝 처리 |
| **generate**         | 1024MB, 3분 | 1536MB, 5분  | 안정적인 제목 생성                   |
| **save_prompt**      | 1024MB, 5분 | 1536MB, 8분  | 대용량 프롬프트 임베딩 처리          |

### 환경 변수 최적화

```python
optimized_env_vars = {
    'PYTHONPATH': '/opt/python',
    'PYTHONUNBUFFERED': '1',
    'LANGCHAIN_TRACING_V2': 'false',  # 디버깅 모드 비활성화
    'TOKENIZERS_PARALLELISM': 'false'  # 토크나이저 병렬 처리 비활성화
}
```

## 📊 모니터링 설정

### CloudWatch 알람

#### Lambda 함수 알람

- **오류율**: 5% 이상 시 알림
- **지연시간**: 30초 이상 시 알림
- **메모리 사용률**: 85% 이상 시 알림 (langchain_router만)

#### API Gateway 알람

- **4XX 오류**: 5분간 20개 이상 시 알림
- **5XX 오류**: 5분간 5개 이상 시 알림
- **지연시간**: 10초 이상 시 알림

#### 비용 알람

- **월 예산**: $200 기준
- **80% 도달**: 실제 비용 알림
- **100% 예상**: 예상 비용 알림

### CloudWatch 대시보드

- **Lambda 성능**: 오류율, 실행시간, 메모리 사용률
- **API Gateway**: 요청 수, 지연시간, 오류율
- **비용 추적**: 일별/월별 비용 트렌드

## 🛡️ 보안 강화

### WAF 보안 규칙

1. **Rate Limiting**: 5분간 2000 요청 제한
2. **Core Rule Set**: AWS 관리형 보안 규칙
3. **Known Bad Inputs**: 악성 입력 차단

### CloudFront 보안 헤더

```javascript
headers["strict-transport-security"] = "max-age=31536000; includeSubDomains";
headers["x-frame-options"] = "DENY";
headers["x-content-type-options"] = "nosniff";
headers["referrer-policy"] = "strict-origin-when-cross-origin";
```

## 🔄 CI/CD 파이프라인

### GitHub Actions 워크플로우

#### 트리거 조건

- `main` 브랜치 푸시
- Pull Request 생성

#### 배포 단계

1. **테스트**: 프론트엔드 테스트 및 린트
2. **백엔드 배포**: CDK를 통한 Lambda 업데이트
3. **프론트엔드 빌드**: React 앱 빌드
4. **S3 배포**: 정적 파일 업로드
5. **캐시 무효화**: CloudFront 캐시 갱신

### 자동 배포 설정

#### 1. GitHub Secrets 설정

```bash
# Repository Settings → Secrets and variables → Actions
AWS_ACCESS_KEY_ID: your-access-key
AWS_SECRET_ACCESS_KEY: your-secret-key
```

#### 2. GitHub Actions 워크플로우 파일 생성

```yaml
# .github/workflows/deploy.yml
name: Deploy TITLE-NOMICS
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to AWS
        run: |
          cd cdk
          cdk deploy --all --require-approval never
```

## 💰 비용 최적화

### 예상 비용 (월)

| 서비스         | 기존 비용 | 최적화 후 | 절감 효과            |
| -------------- | --------- | --------- | -------------------- |
| **Lambda**     | $20-40    | $15-30    | ARM64 아키텍처 적용  |
| **CloudFront** | $5-15     | $3-10     | Price Class 100 적용 |
| **S3**         | $5-10     | $2-5      | Lifecycle 정책 적용  |
| **총합**       | $30-65    | $20-45    | **30% 절감**         |

### 비용 절약 전략

#### 1. S3 Lifecycle 정책

```python
lifecycle_rules = [
    {
        "prompt_bucket": {
            "transition_to_ia": 30,      # 30일 후 IA
            "transition_to_glacier": 90,  # 90일 후 Glacier
            "expiration": 365            # 1년 후 삭제
        }
    }
]
```

#### 2. Lambda 최적화

- **ARM64 아키텍처**: 20% 비용 절감
- **Provisioned Concurrency**: 프로덕션에서만 활성화
- **메모리 최적화**: AWS Lambda Power Tuning 도구 사용

#### 3. CloudFront 최적화

- **Price Class 100**: 북미/유럽만 사용
- **지역 제한**: 한국, 미국만 허용
- **압축 활성화**: 데이터 전송량 감소

## 🚨 문제 해결

### 자주 발생하는 문제

#### 1. Lambda 메모리 부족

```
증상: "Task timed out after X seconds" 또는 메모리 부족 오류
해결: 메모리 크기를 3008MB로 증가, 타임아웃 10분으로 연장
```

#### 2. CloudFront 캐시 문제

```
증상: 새 배포 후에도 이전 버전이 표시됨
해결: 자동 캐시 무효화 또는 수동으로 "/*" 경로 무효화
```

#### 3. API Gateway CORS 오류

```
증상: 프론트엔드에서 API 호출 시 CORS 오류
해결: API Gateway에서 CORS 설정 확인 및 OPTIONS 메서드 추가
```

#### 4. GitHub Actions 권한 오류

```
증상: 배포 시 AWS 권한 부족 오류
해결: IAM 역할 권한 확인 및 GitHub Secrets 재설정
```

### 디버깅 도구

#### 1. CloudWatch Logs Insights 쿼리

```sql
-- Lambda 오류 분석
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
| sort @timestamp desc
```

#### 2. X-Ray 트레이싱

```python
# Lambda 함수에 X-Ray 트레이싱 활성화
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture('lambda_handler')
def lambda_handler(event, context):
    # 함수 로직
    pass
```

#### 3. 성능 모니터링 명령어

```bash
# Lambda 메트릭 조회
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=bedrock-diy-langchain-router-auth \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average

# API Gateway 메트릭 조회
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=bedrock-diy-api-auth \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Sum
```

## 📈 성능 테스트

### 부하 테스트

```bash
# k6를 사용한 부하 테스트
k6 run --vus 10 --duration 30s load-test.js
```

### 성능 벤치마크

```javascript
// load-test.js
import http from "k6/http";
import { check } from "k6";

export default function () {
  const response = http.post("https://your-api-url/generate", {
    article: "test article content...",
  });

  check(response, {
    "status is 200": (r) => r.status === 200,
    "response time < 30s": (r) => r.timings.duration < 30000,
  });
}
```

## 🎯 성능 목표

### 응답 시간 목표

- **제목 생성**: 평균 15초 이내
- **채팅 응답**: 평균 5초 이내
- **프롬프트 업로드**: 평균 10초 이내

### 가용성 목표

- **업타임**: 99.9% 이상
- **오류율**: 1% 이하
- **동시 사용자**: 100명 이상 지원

### 비용 목표

- **월 운영 비용**: $50 이하
- **사용자당 비용**: $0.50 이하
- **비용 증가율**: 월 10% 이하

## 🔮 향후 개선 계획

### 단기 개선 (1-2개월)

1. **Lambda Layer 최적화**: 의존성 크기 감소
2. **DynamoDB 최적화**: GSI 및 쿼리 패턴 개선
3. **Bedrock 모델 최적화**: 더 빠른 모델 적용

### 중기 개선 (3-6개월)

1. **OpenSearch 도입**: 벡터 검색 성능 향상
2. **Multi-Region 배포**: 지연시간 감소
3. **캐싱 전략**: Redis 또는 ElastiCache 도입

### 장기 개선 (6개월 이상)

1. **Kubernetes 마이그레이션**: EKS 기반 컨테이너 배포
2. **ML 파이프라인**: 자동 모델 튜닝
3. **실시간 분석**: Kinesis 기반 스트리밍 처리

## 📞 지원 및 문의

### 문제 신고

- **GitHub Issues**: 기술적 문제 및 버그 신고
- **CloudWatch 알람**: 실시간 시스템 모니터링
- **SNS 알림**: 중요한 이벤트 알림

### 성능 최적화 문의

- 시스템 성능 개선 제안
- 비용 최적화 상담
- 확장성 계획 수립

이 가이드를 통해 TITLE-NOMICS 시스템의 성능을 최적화하고 안정적인 운영을 달성할 수 있습니다.
