# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (한글 폰트 + curl)
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    fonts-nanum-coding \
    fontconfig \
    curl \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/chroma_db /app/data/chatbot_db /app/data/reports /app/data/regulations /app/data/json_reports

# 포트 노출
EXPOSE 8888

# 환경변수 설정
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8888

# 실행 명령
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]
