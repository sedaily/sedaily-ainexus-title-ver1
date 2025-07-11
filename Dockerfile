# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 Python 패키지 설치
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Streamlit 설정
EXPOSE 8080

# 헬스체크 추가
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health

# Streamlit 앱 실행
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"] 