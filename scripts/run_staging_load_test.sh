#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENV_DIR=${GAZFEST_VENV:-"$PROJECT_DIR/venv"}
REDIS_PORT=${STAGING_REDIS_PORT:-16379}
STUB_PORT=${STAGING_STUB_PORT:-19001}
WEB_PORT=${STAGING_WEB_PORT:-18020}
RUNTIME_DIR=$(mktemp -d /var/tmp/gazfest-staging.XXXXXX)

PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
  "$VENV_DIR/bin/python" - <<PY 2>/dev/null || true
from redis import Redis
Redis(host="127.0.0.1", port=$REDIS_PORT).shutdown(save=False)
PY
  rm -rf "$RUNTIME_DIR"
}
trap cleanup EXIT

redis-server \
  --bind 127.0.0.1 \
  --port "$REDIS_PORT" \
  --save "" \
  --appendonly no \
  --dir "$RUNTIME_DIR" \
  --daemonize yes \
  --pidfile "$RUNTIME_DIR/redis.pid"

COMMON_ENV=(
  env
  PYTHONPATH="$PROJECT_DIR"
  SECRET_KEY=staging
  DATABASE_URL="sqlite:///$RUNTIME_DIR/staging.db"
  REDIS_URL="redis://127.0.0.1:$REDIS_PORT/0"
  CELERY_BROKER_URL="redis://127.0.0.1:$REDIS_PORT/1"
  CELERY_RESULT_BACKEND="redis://127.0.0.1:$REDIS_PORT/2"
  MAX_BOT_TOKEN=staging-token
  MAX_WEBHOOK_SECRET=staging-secret
  MAX_API_BASE_URL="http://127.0.0.1:$STUB_PORT"
  OPENAI_API_KEY=staging-key
  OPENAI_BASE_URL="http://127.0.0.1:$STUB_PORT/v1"
  OPENAI_MODEL=gpt-5.6-terra
  MAX_CA_CERT_PATH="$PROJECT_DIR/certs/russian_trusted_root_ca.pem"
)

STUB_OPENAI_DELAY_SECONDS=${STUB_OPENAI_DELAY_SECONDS:-0.2} \
  "$VENV_DIR/bin/python" "$PROJECT_DIR/scripts/staging_stub_server.py" \
  >"$RUNTIME_DIR/stubs.log" 2>&1 &
PIDS+=("$!")

"${COMMON_ENV[@]}" "$VENV_DIR/bin/gunicorn" \
  --workers 3 --threads 4 --worker-class gthread \
  --bind "127.0.0.1:$WEB_PORT" --timeout 30 \
  --access-logfile /dev/null --error-logfile "$RUNTIME_DIR/web.log" \
  wsgi:app &
PIDS+=("$!")

"${COMMON_ENV[@]}" "$VENV_DIR/bin/celery" \
  -A app.celery_app.celery worker \
  --loglevel=warning --pool=threads --concurrency=40 \
  --queues=answers --hostname=staging-answers@%h \
  >"$RUNTIME_DIR/answers.log" 2>&1 &
PIDS+=("$!")

"${COMMON_ENV[@]}" "$VENV_DIR/bin/celery" \
  -A app.celery_app.celery worker \
  --loglevel=warning --pool=threads --concurrency=8 \
  --queues=system --hostname=staging-system@%h \
  >"$RUNTIME_DIR/system.log" 2>&1 &
PIDS+=("$!")

ready=false
for _ in {1..100}; do
  if curl -fsS "http://127.0.0.1:$WEB_PORT/health" >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1:$STUB_PORT/metrics" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 0.2
done

if [[ "$ready" != true ]]; then
  echo "staging services did not become ready" >&2
  tail -n 30 "$RUNTIME_DIR"/*.log >&2 || true
  exit 1
fi

"$VENV_DIR/bin/python" "$PROJECT_DIR/scripts/staging_load_test.py" \
  --url "http://127.0.0.1:$WEB_PORT/max/webhook" \
  --secret staging-secret \
  --broker "redis://127.0.0.1:$REDIS_PORT/1" \
  --metrics "http://127.0.0.1:$STUB_PORT/metrics" \
  --messages "${STAGING_MESSAGES:-1000}" \
  --concurrency "${STAGING_CONCURRENCY:-100}" \
  --drain-timeout "${STAGING_DRAIN_TIMEOUT:-180}"
