#!/bin/bash

# TITLE-NOMICS 배포 스크립트 (인증 비활성화 버전)
# 로그인 문제 해결을 위해 인증을 임시로 비활성화한 상태로 배포

echo "🚀 TITLE-NOMICS 배포 시작 (인증 비활성화 모드)"
echo "⚠️  주의: 인증이 비활성화되어 있습니다. 프로덕션 환경에서는 사용하지 마세요."

# 현재 디렉토리 확인
echo "📁 현재 디렉토리: $(pwd)"

# CDK 디렉토리로 이동
cd cdk

# Python 가상환경 활성화
echo "🐍 Python 가상환경 활성화"
source .venv/bin/activate

# 의존성 설치
echo "📦 의존성 설치"
pip install -r requirements.txt

# CDK 부트스트랩 (필요한 경우)
echo "🥾 CDK 부트스트랩 확인"
cdk bootstrap --profile default

# CDK 배포
echo "🚀 CDK 스택 배포"
cdk deploy --require-approval never --profile default

echo "✅ 배포 완료!"
echo "🔗 API Gateway URL을 확인하고 프론트엔드 설정을 업데이트하세요."
echo "⚠️  인증이 비활성화되어 있으므로 테스트 후 인증을 다시 활성화하세요." 