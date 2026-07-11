#!/bin/sh
set -eu

LOG_DIR="${LOG_DIR:-/app/logs}"
LOG_FILE="$LOG_DIR/backend-console.log" sh /logging/tee-rotate.sh backend-console sh -c '
  python -m app.db.readiness
  alembic upgrade head
  if [ "${VERBOSE_LOGGING:-false}" = "true" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
  fi
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
'
