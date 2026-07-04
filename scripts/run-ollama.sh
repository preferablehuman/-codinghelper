#!/bin/sh
set -eu

MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
SERVER_HOST="${OLLAMA_HOST:-0.0.0.0:11434}"
CLIENT_HOST="${OLLAMA_CLIENT_HOST:-127.0.0.1:11434}"
REQUIRE_GPU="${OLLAMA_REQUIRE_GPU:-true}"
READY_FILE="${OLLAMA_READY_FILE:-/tmp/ollama-gpu-ready}"

requires_gpu() {
  case "$REQUIRE_GPU" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
    *) return 1 ;;
  esac
}

verify_nvidia_runtime() {
  if ! requires_gpu; then
    echo "ollama gpu requirement disabled require_gpu=$REQUIRE_GPU"
    return
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "OLLAMA_REQUIRE_GPU=true but nvidia-smi is not available inside the ollama container" >&2
    exit 1
  fi

  echo "nvidia runtime is visible inside ollama container"
  nvidia-smi -L
  nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.free --format=csv,noheader,nounits || true
}

verify_model_gpu_processor() {
  if ! requires_gpu; then
    touch "$READY_FILE"
    return
  fi

  ps_file="/tmp/ollama-ps.out"
  OLLAMA_HOST="$CLIENT_HOST" ollama ps > "$ps_file"
  cat "$ps_file"

  model_line=$(grep -F "$MODEL" "$ps_file" || true)
  if [ -z "$model_line" ]; then
    echo "OLLAMA_REQUIRE_GPU=true but warmed model is not listed by ollama ps model=$MODEL" >&2
    exit 1
  fi

  case "$model_line" in
    *GPU*)
      echo "ollama gpu verification passed model=$MODEL processor='$model_line'"
      touch "$READY_FILE"
      ;;
    *)
      echo "OLLAMA_REQUIRE_GPU=true but ollama ps does not report GPU execution for model=$MODEL line='$model_line'" >&2
      exit 1
      ;;
  esac
}

echo "starting ollama server host=$SERVER_HOST model=$MODEL"
rm -f "$READY_FILE"
verify_nvidia_runtime
export OLLAMA_HOST="$SERVER_HOST"
ollama serve &
server_pid=$!

stop_server() {
  echo "stopping ollama server"
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" 2>/dev/null || true
}

trap stop_server TERM INT

attempt=0
until OLLAMA_HOST="$CLIENT_HOST" ollama list >/tmp/ollama-list.out 2>&1; do
  attempt=$((attempt + 1))
  echo "waiting for ollama server attempt=$attempt"
  sleep 2
done

echo "ollama server is ready"
echo "pulling persistent model model=$MODEL"
OLLAMA_HOST="$CLIENT_HOST" ollama pull "$MODEL"

echo "available ollama models after pull"
OLLAMA_HOST="$CLIENT_HOST" ollama list

echo "warming ollama model model=$MODEL"
OLLAMA_HOST="$CLIENT_HOST" ollama run "$MODEL" "Reply with OK only."

echo "verifying warmed ollama model uses GPU"
verify_model_gpu_processor

wait "$server_pid"
