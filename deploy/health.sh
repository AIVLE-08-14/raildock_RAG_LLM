#!/bin/bash
set -e

for i in {1..20}; do
  if curl -fsS http://localhost:8888/health > /dev/null; then
    echo "healthy"
    exit 0
  fi
  sleep 3
done

echo "unhealthy"
exit 1