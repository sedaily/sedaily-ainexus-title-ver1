#!/bin/bash

# FAISS Lambda Layer 빌드 스크립트
set -e

echo "FAISS Lambda Layer 빌드 시작..."

# 작업 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAYER_DIR="$SCRIPT_DIR/faiss"
BUILD_DIR="$LAYER_DIR/python"

# 기존 빌드 디렉토리 정리
if [ -d "$BUILD_DIR" ]; then
    echo "기존 빌드 디렉토리 정리..."
    rm -rf "$BUILD_DIR"
fi

# 빌드 디렉토리 생성
mkdir -p "$BUILD_DIR"

# Python 패키지 설치
echo "Python 패키지 설치 중..."
pip install -r "$LAYER_DIR/requirements.txt" -t "$BUILD_DIR"

# FAISS 유틸리티 복사
echo "FAISS 유틸리티 복사..."
cp "$SCRIPT_DIR/../utils/faiss_utils.py" "$BUILD_DIR/"

# Layer ZIP 파일 생성
cd "$LAYER_DIR"
echo "Layer ZIP 파일 생성..."
zip -r faiss-layer.zip python/

echo "FAISS Lambda Layer 빌드 완료: $LAYER_DIR/faiss-layer.zip"
echo ""
echo "AWS CLI로 Layer 업로드:"
echo "aws lambda publish-layer-version \\"
echo "  --layer-name bedrock-diy-faiss-layer \\"
echo "  --description 'FAISS and utilities for vector search' \\"
echo "  --zip-file fileb://faiss-layer.zip \\"
echo "  --compatible-runtimes python3.11" 