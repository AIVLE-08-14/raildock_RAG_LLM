# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치 (한글 폰트 + curl)
RUN apt-get update && apt-get install -y \
    fonts-nanum \
    fontconfig \
    curl \
    && fc-cache -fv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml uv.lock README.md /workdir/
RUN uv sync --no-dev --frozen


COPY . /app

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/chroma_db /app/data/chatbot_db /app/data/reports /app/data/regulations /app/data/json_reports

# 포트 노출
EXPOSE 8888

# 환경변수 설정
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8888

# 실행 명령
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]
