#!/bin/bash
set -e
cd /opt/raildock-llm

if [ ! -f .env ]; then
  echo ".env not found. Create /opt/raildock-llm/.env first" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 어떤 env 파일을 쓸지 결정
if [ -f "$SCRIPT_DIR/image.env" ]; then
  ENV_FILE="$SCRIPT_DIR/image.env"
elif [ -f "/opt/raildock-llm/.env" ]; then
  ENV_FILE="/opt/raildock-llm/.env"
else
  echo "No env file found ($SCRIPT_DIR/image.env or /opt/raildock-llm/.env)" >&2
  exit 1
fi

# ENV_FILE 로드
set -a
source "$ENV_FILE"
set +a

# 기존 .env에서 ECR_URI/IMAGE_TAG 제거 후 새 값으로 덮어쓰기
grep -v '^ECR_URI=' .env | grep -v '^IMAGE_TAG=' > .env.tmp || true

# ✅ 여기 핵심: deploy/image.env 같은 상대경로 쓰지 말고 ENV_FILE 쓰기
cat .env.tmp "$ENV_FILE" > .env
rm -f .env.tmp

echo "==== merged .env ===="
cat .env