#!/bin/sh
set -u

LOG_DIR="${LOG_DIR:-/app/logs}"
LOG_FILE="$LOG_DIR/sandbox-runner-console.log" sh /logging/tee-rotate.sh sandbox-runner-console sh -c '
  if [ "${VERBOSE_LOGGING:-false}" = "true" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload --log-level debug
  fi
  exec uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload --log-level info
'
