#!/bin/bash
set -e
cd /opt/raildock-llm

if [ ! -f .env ]; then
  echo ".env not found. Create /opt/raildock-llm/.env first" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/image.env" ]; then
  source "$SCRIPT_DIR/image.env"
elif [ -f "/opt/raildock-llm/.env" ]; then
  set -a
  source /opt/raildock-llm/.env
  set +a
else
  echo "No env file found (deploy/image.env or /opt/raildock-llm/.env)" >&2
  exit 1
fi

# 기존 .env에서 ECR_URI/IMAGE_TAG 제거 후 새 값으로 덮어쓰기
grep -v '^ECR_URI=' .env | grep -v '^IMAGE_TAG=' > .env.tmp || true
cat .env.tmp deploy/image.env > .env
rm -f .env.tmp

echo "==== merged .env ===="
cat .env

# ---- ECR login (root) ----
AWS_REGION=ap-northeast-2
if ! command -v aws >/dev/null 2>&1; then
  echo "aws cli not found" >&2
  exit 1
fi

ECR_REGISTRY="$(grep '^ECR_URI=' .env | cut -d= -f2 | cut -d/ -f1)"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
docker image prune -f || true