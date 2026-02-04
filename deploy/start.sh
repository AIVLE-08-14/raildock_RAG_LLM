#!/bin/bash
set -e
cd /opt/raildock-llm

if [ ! -f .env ]; then
  echo ".env not found. Create /opt/raildock-llm/.env first" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 어떤 env 파일을 쓸지 결정 (bundle 우선)
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

# 필수값 체크
: "${ECR_URI:?ECR_URI not set}"
: "${IMAGE_TAG:?IMAGE_TAG not set}"

# ✅ 기존 .env에서 ECR_URI/IMAGE_TAG 제거 후, 현재 값으로 다시 추가
grep -v '^ECR_URI=' .env | grep -v '^IMAGE_TAG=' > .env.new || true
printf "ECR_URI=%s\nIMAGE_TAG=%s\n" "$ECR_URI" "$IMAGE_TAG" >> .env.new
mv .env.new .env

echo "==== merged .env ===="
tail -n 20 .env