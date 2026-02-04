#!/bin/bash
set -e
cd /opt/raildock-llm
docker compose -f docker-compose.prod.yml down || true