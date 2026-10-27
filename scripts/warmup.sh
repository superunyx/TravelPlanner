#!/usr/bin/env bash
# scripts/warmup.sh - Wakes up Render free tier backend instances
set -euo pipefail

TARGET_URL="${1:-http://localhost:8000}"
HEALTH_ENDPOINT="${TARGET_URL%/}/health"

echo "Pinging health endpoint: $HEALTH_ENDPOINT"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 45 "$HEALTH_ENDPOINT" || true)

if [ "$STATUS" = "200" ]; then
    echo "Server is awake and healthy! (HTTP 200)"
    exit 0
else
    echo "Server returned HTTP $STATUS. Waiting 15s for cold start..."
    sleep 15
    RETRY_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 45 "$HEALTH_ENDPOINT" || true)
    if [ "$RETRY_STATUS" = "200" ]; then
        echo "Server is now awake! (HTTP 200)"
        exit 0
    else
        echo "Server warmup failed (HTTP $RETRY_STATUS)."
        exit 1
    fi
fi
