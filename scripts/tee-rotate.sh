#!/bin/sh
set -u

if [ "$#" -lt 2 ]; then
  echo "usage: tee-rotate.sh <service-name> <command> [args...]" >&2
  exit 64
fi

SERVICE_NAME="$1"
shift

LOG_DIR="${LOG_DIR:-/app/logs}"
LOG_MAX_BYTES="${LOG_MAX_BYTES:-10485760}"
LOG_MAX_FILES="${LOG_MAX_FILES:-10}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/$SERVICE_NAME.log}"

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

rotate_logs() {
  size=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
  if [ "$size" -lt "$LOG_MAX_BYTES" ]; then
    return
  fi

  max_index=$((LOG_MAX_FILES - 1))
  if [ "$max_index" -lt 1 ]; then
    : > "$LOG_FILE"
    return
  fi

  rm -f "$LOG_FILE.$max_index"
  index=$((max_index - 1))
  while [ "$index" -ge 1 ]; do
    if [ -f "$LOG_FILE.$index" ]; then
      mv "$LOG_FILE.$index" "$LOG_FILE.$((index + 1))"
    fi
    index=$((index - 1))
  done
  if [ -f "$LOG_FILE" ]; then
    mv "$LOG_FILE" "$LOG_FILE.1"
  fi
  touch "$LOG_FILE"
}

write_line() {
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  line="$timestamp [$SERVICE_NAME] $1"
  printf '%s\n' "$line"
  rotate_logs
  printf '%s\n' "$line" >> "$LOG_FILE"
}

FIFO_DIR="${LOG_FIFO_DIR:-/tmp}"
mkdir -p "$FIFO_DIR"
fifo_path="$FIFO_DIR/.${SERVICE_NAME}.$$"
rm -f "$fifo_path"
mkfifo "$fifo_path"

cmd_pid=""
reader_pid=""

forward_signal() {
  if [ -n "$cmd_pid" ]; then
    kill -TERM "$cmd_pid" 2>/dev/null || true
  fi
}

cleanup() {
  rm -f "$fifo_path"
}

trap forward_signal TERM INT
trap cleanup EXIT

write_line "starting command: $*"

(
  while IFS= read -r output_line; do
    write_line "$output_line"
  done < "$fifo_path"
) &
reader_pid=$!

"$@" > "$fifo_path" 2>&1 &
cmd_pid=$!

wait "$cmd_pid"
status=$?

wait "$reader_pid" 2>/dev/null || true
write_line "command exited with status $status"
exit "$status"
