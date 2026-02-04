#!/bin/bash
set -e

mkdir -p /opt/raildock-llm
cd /opt/raildock-llm

if [ ! -f .env ]; then
  echo "/opt/raildock-llm/.env not found. Create it first (LLM APIKEY etc)." >&2
  exit 1
fi

docker --version
docker compose version