# Study Buddy Programming Explainer - Project Memory

## Project Objective

Build a local-first programming explanation assistant that accepts a programming or DSA problem, retrieves approved source material, builds a RAG-style evidence pack, generates a solution through a local model runtime, verifies generated code in an isolated sandbox, and presents an interactive explanation with slide markdown.

## Fixed Location

Implementation lives at:

```text
D:\Development\study buddy
```

Every session should start by reading this file and should end by updating it.

## Target Architecture

Seven default Docker Compose services plus one optional local-model service:

1. `frontend` - React + Vite + TypeScript UI
2. `backend` - provider-neutral FastAPI orchestration and RAG
3. `model-gateway` - internal provider adapter API for health and generation
4. `postgres` - relational application state
5. `qdrant` - vector storage for source chunks
6. `sandbox-runner` - isolated generated-code execution
7. `slide-renderer` - markdown, HTML preview, and PPTX deck export service
8. `ollama` (optional) - local GGUF model server when selected by the gateway

Core rule: PostgreSQL stores application state. Qdrant stores embeddings. The backend orchestrates jobs through a stable model-gateway contract and has no provider-specific dependencies. The sandbox runs generated code. The slide renderer handles deck artifacts.

## Current Status

- Status: MVP scaffold completed with a provider-neutral internal model gateway. The backend remains available when the configured LLM is degraded, and the frontend uses a same-origin `/api` proxy. Gemini is selected in the current local environment; its configured auth key currently receives Google `401 ACCESS_TOKEN_TYPE_UNSUPPORTED`, so model generation remains degraded until that external credential is repaired or replaced.
- Last updated: 2026-07-11
- Current milestone: Phase 1 to Phase 5 application with modular LLM routing, multi-solution generation, verification, and modern learning UI.

## Completed Work

- Created project memory file.
- Planned six-container architecture.
- Added Docker Compose, `.env`, `.env.example`, README, Makefile, data directories, and service Dockerfiles.
- Added FastAPI backend with health, job CRUD/status, result-part endpoints, SQLAlchemy models, and Alembic initial migration.
- Added in-process job pipeline that persists analysis, source metadata, chunks, evidence, solution, tests, verification, explanation, and slide artifacts.
- Added conservative adapter-first retrieval policy and GFG snippet-only compliance defaults.
- Added Qdrant upsert integration with deterministic local embeddings by default and local-path sentence-transformer loading when configured.
- Added Transformers runtime abstraction for local generation.
- Added sandbox-runner with Python and Java execution, compile/runtime/timeout result handling, temporary directories, and process limits.
- Added slide-renderer service that writes deck markdown and exposes a browsable HTML preview.
- Added React/Vite/TypeScript frontend with problem submission, job history, polling result page, evidence, code, tests, explanation, dry-run, and slides tabs.
- Validated Python syntax in-memory for backend and sandbox files.
- Validated slide-renderer JavaScript syntax with `node --check`.
- Validated Docker Compose configuration with `docker compose config --quiet`.
- Reworked Docker Compose so persistent/runtime service data is under `./data/<service>/...`.
- Replaced Docker named volumes for PostgreSQL and Qdrant with host bind mounts at `data/postgres` and `data/qdrant`.
- Added live code bind mounts for `frontend`, `backend`, `sandbox-runner`, and `slide-renderer`.
- Removed app source copies from code-service Dockerfiles so images hold runtime/dependency layers and source changes do not invalidate image builds.
- Added reload/startup commands so backend and sandbox use `uvicorn --reload`, while Node services install dependencies into `data/...` and start from mounted code.
- Moved sandbox generated-code work into `data/sandbox-runner/work`, while keeping `/tmp` as tmpfs for OS-level temporary isolation.
- Fixed sandbox-runner Docker build failure by pinning the base image to `python:3.11-slim-bookworm` and installing `ca-certificates openjdk-17-jdk-headless`.
- Verified `docker compose build sandbox-runner` succeeds.
- Verified Java runtime inside sandbox-runner with `java -version` and `javac -version`; both report OpenJDK 17.0.19.
- Earlier strategy locked model serving to Hugging Face Transformers only; this was superseded on 2026-07-04 by the Ollama `qwen2.5-coder:7b` path because the 30B source download was too large for the target hardware/storage.
- Earlier selection of `Qwen/Qwen3-Coder-30B-A3B-Instruct` as primary generation model is superseded; keep notes only as historical context.
- Recorded `Qwen/Qwen3-Coder-Next` as a high-end research option if hardware allows, not an automatic fallback.
- Recorded `Qwen/Qwen2.5-Coder-7B-Instruct` as a smaller development option only by explicit configuration change.
- Selected `BAAI/bge-m3` as the retrieval embedding model.
- Updated retrieval defaults so curated knowledge-base sources are used even when the user provides no URLs.
- Replaced deterministic solution, test, explanation, and slide generation calls with local Transformers runtime calls.
- Replaced deterministic problem analysis with a model-assisted analysis call while retaining heuristic safeguards for retrieval routing.
- Added a local Transformers repair prompt and pipeline repair loop controlled by `MAX_REPAIR_ATTEMPTS`.
- Added a singleton model runtime provider that only supports the configured `transformers` provider.
- Added strict JSON extraction/validation helpers for model-generated solution, test, and explanation payloads.
- Updated model and embedding cache settings so Hugging Face assets are stored under `data/backend/model-cache`.
- Updated Qdrant collection creation to use the actual embedding vector size instead of assuming 384 dimensions.
- Added hardware-aware model loading defaults for the target machine:
  - adaptive bitsandbytes quantization enabled with `MODEL_QUANTIZATION=auto`, trying 4-bit first and falling back to 8-bit.
  - GPU memory cap set to `10GiB`.
  - CPU memory cap set to `28GiB`.
  - model offload directory set to `/app/data/model-cache/offload`.
  - backend Compose service requests `gpus: all`.
- Added `bitsandbytes` and `accelerate` runtime support for quantized Transformers loading.
- Updated backend PyTorch dependency to `torch==2.7.0+cu128` using the official PyTorch CUDA 12.8 wheel index after a smoke test found `torch==2.5.1` did not support the detected RTX 5070 Ti Laptop GPU `sm_120` capability.
- Validated the new model-backed generator functions with a fake runtime; no real Qwen load was attempted during validation.
- Validated the model-assisted analysis, generation, repair, explanation, and slide path with a fake runtime.
- Built the backend Docker image successfully with the CUDA 12.8 PyTorch stack.
- Verified backend container imports for `torch`, `transformers`, `bitsandbytes`, and `accelerate`.
- Verified CUDA visibility inside the backend container:
  - `torch 2.7.0+cu128`
  - `cuda_available True`
  - `cuda_device_count 1`
  - `device_name NVIDIA GeForce RTX 5070 Ti Laptop GPU`
  - `cuda_tensor_ok True`
- Ran `docker compose up -d --build` successfully after the CUDA 12.8 backend rebuild.
- Verified all six services were running in Docker Compose:
  - frontend on `http://localhost:5173`
  - backend on `http://localhost:8000`
  - PostgreSQL on `localhost:5432`
  - Qdrant on `http://localhost:6333`
  - sandbox-runner on `http://localhost:8100`
  - slide-renderer on `http://localhost:8200`
- Verified health/readiness endpoints:
  - frontend root returned HTTP 200 after Vite finished startup
  - backend `GET /api/health` returned HTTP 200 with database status `ok`
  - sandbox-runner `GET /health` returned HTTP 200
  - slide-renderer `GET /health` returned HTTP 200
  - Qdrant `GET /healthz` and `GET /readyz` returned HTTP 200
  - PostgreSQL `pg_isready` returned accepting connections
- Verified sandbox-runner can execute a passing Python test through `POST /run`.
- Verified slide-renderer can write and serve a smoke deck through `POST /render`.
- Verified backend `GET /api/jobs` returns persisted job history without triggering model loading.
- Added host log folders at `logs/<service>/` for `frontend`, `backend`, `postgres`, `qdrant`, `sandbox-runner`, and `slide-renderer`.
- Added rotating file logging defaults with `LOG_MAX_BYTES=10485760` and `LOG_MAX_FILES=10`.
- Added `VERBOSE_LOGGING` to `.env` and `.env.example`; when enabled it raises backend/sandbox app logging to DEBUG and starts more verbose frontend/PostgreSQL/Qdrant service logging through Compose.
- Added Docker `json-file` console log rotation for every service with 10 files of 10 MB each.
- Added backend logging for HTTP request timing, job creation/history/result reads, job status transitions, pipeline stage counts, model runtime creation/loading/generation, retrieval, embedding fallback, Qdrant upserts, sandbox verification calls, slide renderer calls, and artifact writes.
- Added sandbox-runner logging for HTTP request timing, run requests, process execution, per-test status, timeouts, compile errors, and summaries.
- Added structured slide-renderer console logs for health/render/static-asset requests and render results.
- Added `scripts/tee-rotate.sh` to mirror frontend, PostgreSQL, Qdrant, and slide-renderer command output to console and rotating service log files.
- Documented logging paths and verbosity controls in `README.md`.
- Fixed normal-mode backend logging so SQLAlchemy query logs stay at WARNING unless `VERBOSE_LOGGING=true`; this stops repeated polling SELECT statements from flooding backend logs.
- Fixed backend Ollama warmup failure where the backend sent `keep_alive=-1` in the `/api/generate` JSON payload. The Ollama service accepts `OLLAMA_KEEP_ALIVE=-1` as an environment value, but the HTTP API rejected that per-request field with HTTP 400. Backend requests now omit API `keep_alive` for forever-style values while preserving the service-level residency behavior.
- Added Ollama HTTP error body logging in the backend runtime so future non-2xx model API failures are visible in `logs/backend/backend.log`.
- Verified `logs/backend/backend.log` after restart: backend preload completed, `qwen2.5-coder:7b` is `Q4_K_M`, context length is `8192`, and Ollama reports `size_vram_bytes=5133943438`.
- Verified backend health after the fix: `GET http://localhost:8000/api/health` returned `status=ok`, database `ok`, model loaded `true`, and Ollama provider details.
- Added backend and sandbox startup wrappers so console output is mirrored into rolling `backend-console.log` and `sandbox-runner-console.log` files as well as Docker console output.
- Updated frontend job-result polling to call the lightweight `/api/jobs/{job_id}/status` endpoint while jobs are running, instead of repeatedly fetching full job detail and all related rows.
- Added backend startup recovery for interrupted in-process jobs. Any nonterminal job found at backend startup is marked `FAILED` with a rerun message, because FastAPI background tasks do not survive process restarts.
- Updated the analysis stage current step to `Loading local model and analyzing problem` before the local model runtime is invoked.
- Changed model defaults so the backend no longer lazy-loads the generation model:
  - `MODEL_LAZY_LOAD=false`
  - `MODEL_REQUIRE_CUDA=true`
  - `MODEL_ALLOW_CPU_OFFLOAD=true`
  - `MODEL_ALLOW_DISK_OFFLOAD=false`
  - `MODEL_LOAD_LOG_INTERVAL_SECONDS=30`
- Added backend startup model preload. FastAPI startup now calls the configured model runtime and fails startup if the model cannot load/warm, so jobs cannot enter analysis with an unloaded or unverified model path.
- Added detailed Transformers runtime logging for CUDA inventory, cache state, incomplete Hugging Face artifacts, tokenizer load, model load options, periodic long-load heartbeats, final placement, and CUDA memory.
- Added CUDA placement enforcement for the generation model. With `MODEL_REQUIRE_CUDA=true`, CUDA must be available and used; CPU placement is allowed only when `MODEL_ALLOW_CPU_OFFLOAD=true`, and disk placement is allowed only when `MODEL_ALLOW_DISK_OFFLOAD=true`.
- Updated generation input placement so prompts are moved to an actual CUDA model device and CPU fallback is not silently ignored.
- Updated backend health to include model startup requirement and non-loading model runtime status details when the service is available.
- Updated model placement defaults for the target 12 GB VRAM / 32 GB RAM system:
  - `MODEL_ALLOW_CPU_OFFLOAD=true`
  - `MODEL_ALLOW_DISK_OFFLOAD=false`
  - `MODEL_GPU_MEMORY_LIMIT=9GiB`
  - `MODEL_GPU_MEMORY_UTILIZATION=0.78`
  - `MODEL_KV_CACHE_VRAM_RESERVE=2.5GiB`
  - `MODEL_CPU_MEMORY_LIMIT=24GiB`
- Added dynamic GPU memory planning for `device_map="auto"`. The runtime now chooses the smallest of the configured GPU cap, the configured utilization percentage of total VRAM, and current free VRAM minus the KV-cache reserve, then gives that to Transformers/Accelerate as the CUDA `max_memory`.
- Kept disk offload disabled by default for speed. CPU RAM offload is allowed, but a final placement check still fails if no weights land on CUDA.
- Replaced the older boolean-only 4-bit load behavior with adaptive quantization:
  - `MODEL_QUANTIZATION=auto`
  - `MODEL_QUANTIZATION_FALLBACK=8bit`
  - 4-bit uses bitsandbytes NF4 with double quantization.
  - 8-bit uses bitsandbytes int8 with CPU offload support when `MODEL_ALLOW_CPU_OFFLOAD=true`.
  - Quantization attempts and the selected active quantization are included in runtime status/logs.
- Verified Docker bind mounts for the backend model cache. Docker reported `D:\Development\study buddy\data\backend\model-cache` mounted read-write at `/app/data/model-cache`.
- Stopped the backend container after verifying the active model download was writing into the mounted host cache.
- Added persistent-cache enforcement for the model runtime:
  - `MODEL_PERSISTENT_CACHE_ROOT=/app/data/model-cache`
  - `MODEL_REQUIRE_PERSISTENT_CACHE=true`
  - `MODEL_DOWNLOAD_ON_STARTUP=true`
  - `MODEL_LOCAL_FILES_ONLY=false`
- Aligned Hugging Face cache environment variables so `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, and `TRANSFORMERS_CACHE` all point at the existing mounted cache path under `/app/data/model-cache/huggingface`.
- Added `HF_TOKEN` to local `.env` so Hugging Face Hub requests from the backend can authenticate. The actual token value is intentionally not recorded in project memory; `.env.example` contains only an empty placeholder.
- Added a Hugging Face `snapshot_download` preflight during model startup. It writes/resumes in the mounted cache first; after the snapshot is available, tokenizer and model loading use `local_files_only=True` for that startup pass to avoid a second implicit download path.
- Added a startup persistent-cache check that logs the container mount table entry for the model cache and fails startup if `MODEL_CACHE_DIR` is outside the persistent cache root or the root is not mounted in the container.
- Switched the active generation runtime from Transformers to Ollama after the 30B model proved too large for the target hardware/storage.
- Verified from the official Ollama model page that `qwen2.5-coder:7b` is a 7.62B-parameter code model with `Q4_K_M` quantization and about 4.7 GB size.
- Added `ollama` Compose service using `ollama/ollama:latest`, `gpus: all`, persistent model storage at `data/ollama`, host logs at `logs/ollama`, and health gating on the configured model being present.
- Added `scripts/run-ollama.sh` to start Ollama, pull `OLLAMA_MODEL`, list installed models, warm the model, and log `ollama ps`.
- Hardened Ollama CUDA enforcement in `scripts/run-ollama.sh`: when `OLLAMA_REQUIRE_GPU=true`, startup now fails if `nvidia-smi` is unavailable inside the container or if the warmed model's `ollama ps` line does not report `GPU`.
- Updated the Ollama Compose healthcheck to wait for `/tmp/ollama-gpu-ready`, which is written only after the model is warmed and GPU verification passes.
- Fixed the Ollama image entrypoint mismatch that produced `Error: unknown command "sh" for "ollama"` by setting `entrypoint: []` and using an exec-form shell command for the logging/startup wrapper.
- Changed `.env`, `.env.example`, and backend defaults to `MODEL_PROVIDER=ollama`, `MODEL_NAME_OR_PATH=qwen2.5-coder:7b`, `OLLAMA_MODEL=qwen2.5-coder:7b`, `OLLAMA_NUM_CTX=8192`, `OLLAMA_KEEP_ALIVE=-1`, and `OLLAMA_REQUIRE_GPU=true`.
- Added `backend/app/model_runtime/ollama_runtime.py`, which waits for Ollama, verifies model inventory, warms via `/api/generate`, logs quantization/size/context details, checks `/api/ps`, and fails startup when `OLLAMA_REQUIRE_GPU=true` but `size_vram` is zero.
- Updated the model provider to lazy-import the old Transformers runtime only when `MODEL_PROVIDER=transformers`; the Transformers files remain available but unused by default.
- Removed backend GPU ownership from Compose; GPU access is now assigned to the Ollama service.
- Confirmed the host `data/backend/model-cache` has no Hugging Face model payloads and no files over 1 GiB exist under `data` after cleanup.
- Reworked slide markdown prompting to request a concise six-slide learner deck: problem, observation, plan, dry run, code walkthrough, and complexity/tests/pitfalls.
- Added `pptxgenjs` to the slide-renderer and replaced the old HTML-only `<pre>` renderer with a parser that writes `deck.md`, a slide-card HTML preview, and `deck.pptx`.
- Added simple PowerPoint graphics: accent rails, concept bubbles, flow boxes, dry-run tables, and code panels.
- Updated the backend slide client/pipeline to request PPTX, store `pptx_path`, and log the returned PPTX artifact.
- Updated the frontend slide viewer to show a `Download PPTX` link when available.
- Fixed frontend TypeScript build hygiene by adding the Vite client type shim, `@types/react-dom`, and ES2022 libs for existing `.at()` calls.
- Validated this update with backend `compileall`, `node --check slide-renderer/server.js`, `docker compose config --quiet`, a frontend production build, and a live slide-renderer smoke test.
- The slide-renderer smoke test produced a valid six-slide PPTX (`[Content_Types].xml` and `ppt/presentation.xml` present) before the smoke artifact and stopped test container were removed.
- Verified Ollama container CUDA visibility on 2026-07-04 with `docker compose run --rm --no-deps --entrypoint sh ollama ... nvidia-smi ...`.
  - The `ollama/ollama` image was pulled during this check.
  - Inside the Ollama container, `nvidia-smi -L` reported `NVIDIA GeForce RTX 5070 Ti Laptop GPU`.
  - The query output reported driver `610.62`, total VRAM `12227 MiB`, and free VRAM `11944 MiB`.
  - The model itself was not pulled during this CUDA visibility check.
- Verified the Ollama entrypoint fix with `docker compose run --rm --no-deps ollama /bin/sh -c "echo entrypoint-ok"`; output was `entrypoint-ok`.

## Pending Work

- Expand source adapters from conservative seed/user-URL metadata to richer approved-source retrieval.
- Add full frontend automated tests.
- Add full backend integration tests against PostgreSQL and Qdrant.
- Add package lockfiles after the first successful npm install/build.
- Verify mounted-code reload behavior once Docker Desktop is running.
- Run a first full job after the Ollama model is pulled into `data/ollama`, then tune `OLLAMA_NUM_CTX`, generation token limits, and repair attempts based on actual latency and VRAM use.
- Consider moving long-running jobs out of FastAPI in-process background tasks if restart-resumability becomes required.
- Replace or repair the current Gemini auth key, which Google rejects with `401 ACCESS_TOKEN_TYPE_UNSUPPORTED`, then run one end-to-end online job.

## Design Decisions

- Use Docker Compose only for v1.
- Use a modular monolith backend instead of splitting internal RAG/generation services.
- Keep provider orchestration outside the application backend. All generation crosses the model-gateway `/health` and `/generate` API; provider changes are gateway-only configuration/adapter work.
- Preload the configured generation model during backend startup. Local containers should not report backend startup complete until the configured model is loaded/warmed or has failed loudly.
- Use adapter-first retrieval and avoid paid search APIs or external LLM APIs.
- Use Ollama as the active local model-serving path because it directly supports the desired `Q4_K_M` quantized coder model. Keep Hugging Face Transformers runtime files available but unused by default.
- Default generation model is `qwen2.5-coder:7b` through Ollama.
- Default embedding model is `BAAI/bge-m3`.
- Target machine defaults assume 32 GB RAM and 12 GB VRAM. Use Ollama `Q4_K_M`, GPU residency checks, `OLLAMA_NUM_CTX=8192`, and keep the model warm with `OLLAMA_KEEP_ALIVE=-1`.
- User-provided source URLs are optional. The app must have curated automatic retrieval sources and should not depend on the user supplying URLs.
- Treat Python and Java as MVP execution languages.
- Keep C++, JavaScript visible as future language options but disabled in the UI until implemented.
- Keep container-owned persistent/runtime data under `./data/<service>/...`.
- Keep application source mounted into code services during local development to avoid rebuilding images for code-only changes.
- Keep sandbox execution work under `data/sandbox-runner/work`, cleaned per run; keep `/tmp` tmpfs for isolation.
- Keep service logs under `./logs/<service>/...`, with app-level or wrapper-level rolling files and Docker console log rotation both capped at 10 x 10 MB by default.

## Standing Engineering Guidelines

- Start every session by reading this checkpoint.
- End every implementation session by updating this checkpoint with status, decisions, changed files, validation, known issues, and next steps.
- Prefer the simplest understandable approach and readable code.
- Change only files directly related to the current requirement.
- Ask when an important product, hardware, data, or behavior choice cannot be discovered from the project context.
- Do not invent unsupported choices; document researched defaults and sources.

## Important Commands

```powershell
cd "D:\Development\study buddy"
copy .env.example .env
docker compose up --build
```

After the first build, code-only edits should usually need only:

```powershell
docker compose restart backend
docker compose restart sandbox-runner
docker compose restart slide-renderer
docker compose restart frontend
```

```powershell
docker compose exec backend alembic upgrade head
docker compose exec backend pytest
docker compose exec sandbox-runner pytest
docker compose build backend
docker compose run --rm --no-deps backend python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Useful local URLs while the stack is running:

```text
Frontend:       http://localhost:5173
Backend health: http://localhost:8000/api/health
Sandbox health: http://localhost:8100/health
Slides health:  http://localhost:8200/health
Qdrant health:  http://localhost:6333/healthz
```

Logging defaults:

```powershell
# In .env
VERBOSE_LOGGING=false
LOG_MAX_BYTES=10485760
LOG_MAX_FILES=10
MODEL_LAZY_LOAD=false
MODEL_REQUIRE_CUDA=true
MODEL_ALLOW_CPU_OFFLOAD=true
MODEL_ALLOW_DISK_OFFLOAD=false
MODEL_LOAD_LOG_INTERVAL_SECONDS=30
MODEL_GPU_MEMORY_LIMIT=9GiB
MODEL_GPU_MEMORY_UTILIZATION=0.78
MODEL_KV_CACHE_VRAM_RESERVE=2.5GiB
MODEL_CPU_MEMORY_LIMIT=24GiB
MODEL_PERSISTENT_CACHE_ROOT=/app/data/model-cache
MODEL_REQUIRE_PERSISTENT_CACHE=true
MODEL_DOWNLOAD_ON_STARTUP=true
MODEL_LOCAL_FILES_ONLY=false
MODEL_QUANTIZATION=auto
MODEL_QUANTIZATION_FALLBACK=8bit
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_NUM_CTX=8192
OLLAMA_KEEP_ALIVE=-1
OLLAMA_REQUIRE_GPU=true
```

Host log folders:

```text
logs/frontend
logs/backend
logs/ollama
logs/postgres
logs/qdrant
logs/sandbox-runner
logs/slide-renderer
```

## Known Issues And Recovery Notes

- The first Docker build may take time because backend dependencies still include Transformers, Torch, and sentence-transformers for the unused Transformers runtime path.
- The first Ollama startup will download `qwen2.5-coder:7b` once into `data/ollama`; official Ollama metadata lists it around 4.7 GB, not the >100 GiB Qwen3 cache path.
- Online retrieval depends on local network availability and source terms. The scaffold avoids bulk crawling and starts conservatively.
- Problem analysis, solution, test, repair, explanation, and slide generation now call the configured model runtime. With current defaults that runtime is Ollama, not Transformers.
- The Ollama model was not pulled during the implementation session to avoid starting a 4.7 GB download without an explicit full-stack run. Backend startup will pull/warm through the Ollama service when the stack is started.
- Python syntax validation used the bundled Codex Python because the system `python` launcher points to a missing local install.
- `docker compose up --build` was attempted on 2026-07-04 and failed because the Docker Desktop Linux engine pipe was not available: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` Start Docker Desktop, ensure the Linux engine is running, then retry `docker compose up --build`.
- A later sandbox-runner build failed on the floating `python:3.11-slim` base while installing `openjdk-17-jdk-headless`. The fix was to pin the sandbox base image to Debian Bookworm: `python:3.11-slim-bookworm`.
- An initial backend GPU smoke test with `torch==2.5.1` saw the GPU but warned that the installed PyTorch build did not support `sm_120`. This was fixed by moving to `torch==2.7.0+cu128`; the follow-up smoke test succeeded without that warning and completed a CUDA tensor operation.
- Full six-service `docker compose up -d --build` succeeded after the backend CUDA 12.8 rebuild.
- Frontend startup runs `npm install --package-lock=false` into `data/frontend/node_modules`; npm reported 2 audit findings during startup, 1 low and 1 moderate. These have not been remediated yet.
- Logging changes were validated with Python compile checks, `node --check` for the slide renderer, and `docker compose config --quiet`. They were not live-smoke-tested in containers during the logging update because Docker Desktop's Linux engine was unavailable in the current session.
- Follow-up logging/job-state fix was live-validated on 2026-07-04: backend, sandbox-runner, slide-renderer, and frontend health checks passed; host log files were written under `logs/<service>/`; backend SQLAlchemy polling spam was absent in normal mode; previously stuck job `8713558f-faa5-40a5-9c7a-cccf86cddce5` was marked `FAILED` with an interrupted-by-restart rerun message.
- Strict startup model preload was live-validated on 2026-07-04:
  - `docker compose up -d --force-recreate backend` recreated the backend with strict CUDA settings.
  - `logs/backend/backend.log` and `logs/backend/backend-console.log` received concurrent model startup logs.
  - The logs showed CUDA available inside the backend with `torch 2.7.0+cu128`, CUDA 12.8, one `NVIDIA GeForce RTX 5070 Ti Laptop GPU`, about 11.9 GiB total VRAM, and about 10.8 GiB free VRAM.
  - The logs from that earlier strict-CUDA validation showed `device_map={'': 0}` with CPU/disk offload disabled; the later placement policy now allows CPU offload while keeping disk offload disabled.
  - The logs showed the Qwen cache was incomplete and actively growing: roughly 42.1 GiB at startup, then 43.9 GiB during heartbeat checks, with many `.incomplete` files.
  - `nvidia-smi` from inside the backend container showed the backend Python process visible on the GPU but only about 154 MiB GPU memory while the heartbeat reported `allocated_bytes=0` and `reserved_bytes=0`; this means the model had not reached CUDA weight placement yet and was still in the download/cache stage.
  - Backend health was not available during this preload because FastAPI startup is intentionally blocked until model load completes or fails.
- Mounted-cache verification was performed on 2026-07-04:
  - `docker inspect studybuddy-backend-1` showed a read-write bind mount from `D:\Development\study buddy\data\backend\model-cache` to `/app/data/model-cache`.
  - The host cache path `data/backend/model-cache/huggingface/models--Qwen--Qwen3-Coder-30B-A3B-Instruct` existed with 67 files, about 50.75 GiB, and 48 `.incomplete` files after stopping the active download.
  - `docker compose stop backend` stopped the backend; `docker compose ps -a backend` showed `studybuddy-backend-1` exited.
- Model cache cleanup was performed on 2026-07-04 while the backend was stopped:
  - Removed only stale Hugging Face `.incomplete` and `.lock` files under `data/backend/model-cache/huggingface`.
  - Removed 84 files, freeing about 55.8 GiB.
  - Completed Hugging Face source blobs were intentionally kept; bitsandbytes 4-bit/8-bit quantization happens during model load and still requires the source weight shards in the cache.
- Earlier Qwen3 Transformers placement work attempted GPU-first placement with CPU offload and a 2.5 GiB KV-cache reserve, but the current default no longer uses that 30B model.
- Qwen model notes researched on 2026-07-04:
  - `Qwen/Qwen3-Coder-30B-A3B-Instruct` is Apache-2.0, Transformers-compatible, coding-focused, 30.5B total / 3.3B active parameters, with 262K native context.
  - `Qwen/Qwen3-Coder-Next` is Transformers-compatible and coding-agent focused, 80B total / 3B active parameters, with 262K native context, but is a larger hardware/storage commitment.
  - `Qwen/Qwen2.5-Coder-7B-Instruct` is Apache-2.0, Transformers-compatible, coding-focused, and smaller for constrained local development.
  - `BAAI/bge-m3` supports dense retrieval and sentence-transformers/Transformers usage for embeddings.
- Processing-log verification and fixes on 2026-07-04:
  - Current failing job was `6d19777b-4a49-484f-9617-f31491313deb` for Java "Sort Characters By Frequency".
  - Initial backend logs showed the older Qdrant vector-size mismatch had already self-healed and Ollama was loaded as `qwen2.5-coder:7b` with `Q4_K_M`, context 8192, and about 5.13 GB reported in VRAM.
  - The active failures moved to generated-code verification: Java first failed because the sandbox used `RLIMIT_AS`, which prevented JVM startup. Java now disables the OS address-space limit and relies on explicit JVM heap/metaspace/code-cache/stack limits plus process timeout. A direct Java sandbox smoke test passed.
  - Java runner now detects `public class` / first class name, writes the matching `.java` file, logs compile stdout/stderr previews, and can run generated `Solution` or `Main` classes.
  - Backend prompts now require standalone stdin/stdout programs for online-judge style problems and forbid hard-coded sample-only `main` methods.
  - Java solution normalization adds standard `java.util.*` and `java.io.*` imports to avoid repeated missing-standard-import repair loops.
  - Ollama generation logs now include the `done` flag and retries once for JSON-mode calls if Ollama returns a non-final `done=false` response.
  - Test parsing now tolerates a single JSON test object in addition to a bare array or wrapped `tests` / `test_cases` / `cases` array.
  - Frequency-sort tests are post-processed for multiple-valid-output cases: ambiguous tie outputs get `expected_output=null`, and no-tie control cases are added to keep verification meaningful.
  - Final rerun completed with verification `PASSED`, 4 passed and 0 failed, then generated explanation and slide artifacts successfully. Backend and sandbox log tails showed no fresh errors after completion.
- UI coding-workspace update on 2026-07-04:
  - Main app shell now uses a compact coding-assistant theme with a dark top bar, terminal/code accents, emerald focus states, and a subtle grid background.
  - New problem form defaults to Java, removes the obsolete user URL/source URL input, and sends `source_urls: []`.
  - Backend `JobCreate` default language is now Java.
  - Result page tabs moved from the top row into a left analysis rail with icon tabs for explanation, code, tests, sources, dry run, and slides.
  - Code tab is now an editable Monaco workspace with reset, custom stdin, optional exact expected output, and a run button.
  - Added backend `POST /api/execute` as a browser-facing sandbox proxy. It supports Java/Python, custom stdin, optional expected output, timeout, and memory limits.
  - Code execution smoke test through backend passed with Java: `PASSED`, 1 passed, 0 failed.
  - Frontend TypeScript validation passed by temporarily junctioning `frontend/node_modules` to `data/frontend/node_modules` and removing the junction afterward.
  - Vite production build could not be completed on the Windows host because `data/frontend/node_modules` is container-installed and lacks Rollup's Windows optional native package. The dev frontend still responded with HTTP 200 at `http://localhost:5173`.
- Modern UI and learning-ladder update on 2026-07-04:
  - App shell now has persistent light/dark mode, a wider `max-w-[1760px]` workspace, fade/rise animations, dark-mode global markdown styles, and larger readable form/result surfaces.
  - Result page now shows job summary metrics for approach count, test count, and detected pattern, while retaining the left analysis rail.
  - Backend solution generation now requests a three-step approach ladder: `BRUTE_FORCE`, `IMPROVED`, and `OPTIMAL`. All generated variants are stored as `GeneratedSolution` rows, and the optimal/expected/final solution is selected for verification.
  - Code tab now accepts all stored solutions, sorts them as an implementation ladder, lets users switch between variants, and keeps the active variant editable/runnable with custom stdin and optional expected output.
  - Dry-run tab now combines approach buildup, optimal pseudocode/logic stub, execution trace markdown, step guidance, and pitfalls. New explanation prompts require a code-logic stub, step table, state changes, and main decision point.
  - Test generation now recommends at least 10 meaningful cases when possible and removes the previous maximum cap. The frontend test panel displays the recommended minimum and allows any number of generated cases.
  - Slide prompts now require an eight-slide learner deck covering approach ladder, brute force, improved, optimal, dry-run visualization, code trace, complexity, tests, and pitfalls. The slide renderer no longer truncates decks to six slides and now allows up to twelve parsed slides.
  - Frontend, backend, and slide-renderer services were restarted with `docker compose restart frontend backend slide-renderer` so mounted code changes were loaded by the live app.
  - Validation passed: backend `py_compile`, `node --check slide-renderer/server.js`, frontend `tsc --noEmit`, backend health, slide-renderer health, and frontend HTTP 200.
  - Browser visual verification passed on the live result/code workspace in light and dark mode with no horizontal overflow. Existing old jobs only show one `Verified solution`; newly generated jobs should show the full three-approach ladder.
  - Vite production build is still blocked on the Windows host by the existing container-installed `data/frontend/node_modules` missing `@rollup/rollup-win32-x64-msvc`; this is the same Rollup optional dependency issue as before.
- Explanation consolidation, test-suite execution, and retrieval update on 2026-07-04:
  - Removed `Dry run` and `Slides` from the result navigation. The `Explanation` workspace now owns solution selection, reasoning, dry-run/code logic, GFG-style illustration cards, proof-run execution, pitfalls, complexity, SVG illustration download, PPTX download, and HTML preview links.
  - The Code tab and Tests tab now support executing the full generated test suite through the existing backend execute API. The response includes per-test results and `average_execution_time_ms`.
  - Backend `POST /api/execute` now accepts either a single custom input or a `tests` array. Stored verification runs now save average execution time instead of always storing zero.
  - Solution generation now asks for at least `BRUTE_FORCE` and `OPTIMAL`, with `IMPROVED` only when meaningfully different. Backend post-processing drops duplicate/similar variants by comparing normalized code and complexity.
  - Explanation prompts now require per-approach dry-run sections and GFG-style illustration tables with concrete state changes. Slide prompts now require an approach comparison table and concrete illustration/dry-run content.
  - Retrieval now queries local Qdrant RAG first, converts high-confidence local hits into reusable sources, then enriches with approved fetched/curated sources up to a balanced target. Stack problems now include the GFG balanced-parentheses article as a curated source candidate.
  - Validation passed: backend `py_compile`, slide-renderer `node --check`, frontend `tsc --noEmit`, backend health, slide-renderer health, frontend HTTP 200, and live `/api/execute` multi-test Java smoke returned `PASSED` with average runtime.
  - Browser visual check passed on the consolidated Explanation page: only Explanation/Code/Tests/Sources remain in the rail, download controls are visible, and the page has no horizontal overflow.
- Multi-solution reliability, Gemini routing, and home UI revamp on 2026-07-11:
  - Root cause of one-solution jobs was the combined approach request: a truncated or partially valid JSON response was accepted as long as it contained one usable variant.
  - Solution generation now makes independent structured model requests for `BRUTE_FORCE`, `IMPROVED`, and `OPTIMAL`. Brute force and optimal are required; the intermediate approach may be omitted only if it is invalid or deduplicates as algorithmically equivalent.
  - Added focused tests proving three independent requests are made and proving an invalid optional intermediate response still returns the required brute-force/optimal pair.
  - Added a server-side Gemini REST runtime selected with `MODEL_PROVIDER=gemini`. It verifies the configured model, uses `x-goog-api-key`, supports JSON response mode, retries transient quota/server/network failures, logs token usage, and never returns the key in status data.
  - Added `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL`, timeout, and retry settings. The stable default is `gemini-2.5-flash`; `.env.example` and README document setup and the no-Ollama Compose command.
  - Removed the backend's hard Compose dependency on Ollama so the online service set can start without pulling or warming a local model. Ollama remains the default provider and continues to work when its service is started.
  - Rebuilt the input experience with a product-specific hero, clearer form hierarchy, terminal-style problem editor, character count, keyboard submission, language cards, difficulty controls, stronger responsive layout, and live backend runtime/key-route status.
  - Validation passed: all 48 backend Python files parsed, frontend TypeScript completed with no errors using the existing container dependency cache, slide-renderer JavaScript syntax passed, solution-variant tests passed, `docker compose config --quiet` passed, and `git diff --check` passed.
  - Full container and live API checks were not available because the Docker Desktop engine pipe was absent. No Gemini key was present, so no external quota-consuming generation request was attempted.
- Provider-neutral model gateway and fetch-failure repair on 2026-07-11:
  - Verified the browser failure was caused by an explicit mismatch: the backend still selected Ollama while the Ollama Compose service was disabled. Strict backend model preload prevented FastAPI from becoming a reliable application API.
  - Added an independent `model-gateway` FastAPI service with a stable internal `GET /health` and `POST /generate` contract. Gemini and Ollama adapters, credentials, model names, retry logic, and provider HTTP formats now live exclusively behind this boundary.
  - Replaced active backend provider selection with `ModelGatewayRuntime`. Backend configuration now contains only gateway URL/timeouts; active backend, pipeline, API, and frontend code contain no Gemini/Ollama branching.
  - Backend startup now tolerates a degraded or unreachable model gateway. Database/history/UI APIs remain reachable, `/api/health` reports model readiness, and generation failures become explicit provider errors instead of browser `Failed to fetch` failures.
  - Changed the frontend to same-origin `/api` requests and added a Vite container proxy to `backend:8000`, removing browser coupling to hard-coded `localhost:8000`. Added a clear API-unavailable message and generic provider/gateway status UI.
  - The model gateway is available only on the Compose network (`expose`, not a host port), so the provider key cannot be consumed through an unauthenticated host endpoint.
  - Updated `.env.example` to the generic `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, temperature, timeout, and retry contract. Changing providers no longer requires application changes.
  - Live validation passed: rebuilt and started gateway/backend/frontend; backend database health is `ok`; frontend `http://localhost:5173/api/health` successfully proxies to the backend; focused gateway/solution tests report 4 passed; frontend and Vite TypeScript checks pass; gateway source parses; Compose config passes.
  - Live Gemini verification reached Google but the configured 106-character `AQ.` auth key returned `401 UNAUTHENTICATED` with `ACCESS_TOKEN_TYPE_UNSUPPORTED` on both model verification and the recommended Interactions endpoint. The gateway now reports a safe actionable authentication error while keeping the application operational. The credential value was never logged or exposed.
- Backend database-startup race repair on 2026-07-11:
  - Reproduced a misleading `Up` backend container whose Uvicorn reload parent survived while the application child exited. PostgreSQL was still recovering, causing both Alembic and `recover_interrupted_jobs()` to receive connection-refused / database-starting errors.
  - Added `app.db.readiness`, which retries a real SQL query for up to 120 seconds before migrations run.
  - Changed `scripts/run-backend.sh` to `set -eu`, run the database readiness gate first, and stop immediately if readiness or migrations fail.
  - Added a backend HTTP healthcheck and changed frontend Compose dependency from `service_started` to `service_healthy`, preventing the UI from starting against a non-serving reload parent.
  - Recreated the services and verified the corrected order in live logs: database readiness passed, Alembic completed, application startup completed, backend became Docker `healthy`, and `http://localhost:5173/api/health` returned API/database `ok`.
- Approach deduplication, truncated JSON recovery, and input UI refinement on 2026-07-11:
  - Explanation generation now uses an 8192-token output budget and retries one malformed or truncated response with an explicit compact-JSON instruction. JSON normalization accepts singleton object arrays and named wrappers, while incomplete root objects are no longer misreported as nested arrays.
  - Each solution approach now gets one regeneration attempt when its payload is invalid, truncated, or implementation-equivalent to an earlier approach. Exact code, near-identical code plus pseudocode/complexity, and strongly matching algorithm structure are deduplicated; similar explanation or intuition alone is explicitly allowed when the implementation differs.
  - Removed the duplicated `solution_variant_prompt` definition. Earlier approaches are now represented to the model with algorithm pattern, pseudocode, and complexity so it can produce a genuinely different next step.
  - Rerunning a job now clears prior sources, evidence, solutions, tests, verification runs, explanations, and slide artifacts before queuing. This prevents old result rows from accumulating into duplicate approach ladders.
  - Removed difficulty from new-job input/API payloads. The database and response fields remain nullable for historical compatibility, while every new problem is analyzed from its statement and constraints.
  - Removed the homepage `What you'll get` section and relocated the primary `Generate solution ladder` control into that sidebar position. The form exposes submit readiness to the external button and retains Ctrl/Cmd+Enter submission.
  - The full backend suite passed with 12 tests after aliasing the imported `tests_prompt` helper so pytest no longer collected it as a test. The frontend production TypeScript/Vite build and `git diff --check` also passed. A live rerun verified cleanup (six sources after rerun rather than accumulated copies), then the free-tier Gemini provider exhausted its quota before generation could complete; end-to-end completion therefore remains externally blocked until quota resets or another provider key/model is configured.
- Provider-neutral structured-output contract and live Gemma completion on 2026-07-12:
  - The recurring `got list` error was traced to Gemma returning bullet-point prose containing an unrelated JSON array. The old backend parser scanned the prose, selected that nested array, and misreported it as the model's root payload.
  - The model gateway now owns a provider-neutral JSON contract. For every `json_mode` request it validates and canonicalizes an object/array, accepts a complete JSON Markdown fence, and retries malformed output up to two times by feeding the invalid response back with a strict reformatting contract.
  - Backend object parsing now searches only for object roots and array parsing only for array roots, preventing nested arrays in prose from masquerading as structured object responses.
  - Gemini transport supports an optional `LLM_JSON_MODEL`, but blank or matching configuration keeps all calls on the selected model. The active setup deliberately uses `gemma-4-31b-it` for both ordinary and structured requests because of free-tier restrictions.
  - Gateway response extraction ignores explicit thought parts and keeps provider-specific response handling behind the gateway. Application/pipeline code remains coupled only to `POST /generate` and never branches on Gemini, Gemma, Ollama, or future provider names.
  - Framework direction: LiteLLM is the preferred future replacement for custom provider adapters and routing/fallback policy; PydanticAI `PromptedOutput` is the preferred typed-schema layer when stage payload schemas are migrated from prompt text. These can be introduced inside the existing gateway boundary without changing frontend or pipeline orchestration.
  - Validation passed with 13 backend tests and 4 gateway contract tests. A live rerun using Gemma completed end to end with three distinct approaches (`BRUTE_FORCE`, `IMPROVED`, `OPTIMAL`), 13 generated tests, verification `PASSED` with 13/13 passing, one explanation, and one slide artifact.
- LangChain model gateway, focused RAG, and teaching-deck upgrade on 2026-07-12:
  - Replaced the gateway's provider-specific runtime selection with one LangChain adapter boundary supporting `nvidia`, `gemini`, `ollama`, `openai`, and `openai_compatible`. Provider, model, base URL, credentials, and JSON model remain environment-only choices; backend and frontend contracts are unchanged.
  - Kept structured-output validation at the gateway boundary. Malformed JSON is canonicalized or retried independently of the selected LangChain chat model, and reasoning/thinking content blocks are excluded from the final response text.
  - Verified LangChain client construction for NVIDIA NIM and Ollama without application changes. The live stack still reports Gemini/Gemma because the current project `.env` contains `LLM_PROVIDER=gemini` and `gemma-4-31b-it`; switching to NVIDIA requires saving the NVIDIA values and recreating only `model-gateway`.
  - Reworked retrieval around direct algorithm and data-structure teaching pages for the selected pattern. Broad Python, Java, API-reference, and generic homepage sources are rejected; evidence ranking favors pattern vocabulary, intuition, invariants, state transitions, complexity, and code-oriented explanations across diverse sources.
  - Replaced text-to-slide conversion with a structured 12-16 slide teaching-deck contract. The narrative covers problem framing, constraints, approach ladder, comparison, state/data structures, two dry runs, code walkthroughs, correctness, verification, complexity, pitfalls, synthesis, and references.
  - The renderer now has purpose-built layouts for title, concept, flow, comparison, dry-run, code, verification, and reference slides; it also saves the structured `deck.json` beside PPTX, Markdown, and HTML artifacts.
  - Validation passed: 18 backend tests, 5 model-gateway tests, slide-renderer fixture test, NVIDIA/Ollama adapter construction, frontend TypeScript/Vite production build, Docker builds for model-gateway and slide-renderer, Compose validation, PPTX visual render inspection, slide overflow inspection, and live same-origin health. The running gateway reports `framework=langchain` and a minimal live structured request returned valid JSON.
- Provider-specific environment isolation on 2026-07-12:
  - Kept `LLM_PROVIDER` as the only selector and replaced generic model, JSON model, API key, and base URL fields with provider-prefixed blocks such as `NVIDIA_LLM_MODEL`, `GEMINI_LLM_MODEL`, and `OLLAMA_LLM_MODEL`.
  - LangChain now resolves only the selected provider's configuration block. Switching providers preserves the other providers' models, endpoints, and credentials without editing application code or copying values into generic variables.
  - Migrated the local `.env` NVIDIA and Gemini values without printing or discarding their credentials; added ready-to-fill Ollama, OpenAI, and OpenAI-compatible blocks.
  - Validation passed with Compose configuration and all 8 model-gateway tests. Runtime restart and external inference were intentionally left to the user.
- Retrieval-first verified solution corpus on 2026-07-12:
  - Added an independent PostgreSQL knowledge domain for canonical problems, textual variants, reusable language/approach solutions, asserting regression tests, compliant knowledge sources/chunks, match traces, and external ingestion diagnostics. Job deletion uses `SET NULL` provenance links and cannot cascade-delete canonical knowledge.
  - Migration `0002_retrieval_corpus` preserves job history, adds verification hashes/version metadata, enables `pg_trgm` when permitted, creates trigram indexes conditionally, and is reversible. Upgrade passed against both the existing database and a temporary empty database.
  - Added deterministic Unicode/Markdown/label normalization, stable SHA-256 statement hashes, source identity extraction, sample separation, deterministic semantic flags, Pydantic problem signatures, source/hash lookup before embeddings or model calls, PostgreSQL lexical matching, dedicated Qdrant semantic matching, weighted compatibility scoring, hard-contradiction gates, and advisory LLM equivalence adjudication.
  - Added retrieval routes `EXACT_REUSE`, `EQUIVALENT_ADAPT`, `RELATED_GROUNDING`, `EXTERNAL_DISCOVERY`, and `GENERATE_FRESH`. Exact reuse reverifies stored code through sandbox-runner and skips analysis, external discovery, solution generation, and test generation. Cross-language/equivalent reuse adapts the verified algorithm and must pass stored asserting tests.
  - Every generated solution variant is now independently sandbox-verified. Failed variants remain recorded but are excluded from frontend working-solution views; only passing code hashes can be promoted. Promotion requires a completed/promoting job, at least eight asserting tests by default, zero verification failures, matching code hash, complete payload, no credential signatures, and permitted provenance.
  - Added dedicated Qdrant problem and knowledge collections whose payloads contain stable database IDs rather than authoritative statements/code. Promotion commits PostgreSQL first, then performs retryable/idempotent vector indexing. Added dry-run-capable backfill and PostgreSQL-authoritative Qdrant reconciliation commands.
  - Added approved Stack Exchange and Codeforces API adapters, allowlisted curated-repository metadata, SSRF-safe user URL retrieval, an explicit denied-source policy including automated LeetCode crawling, source-specific storage limits/attribution, typed candidate ranking/ingestion, prompt-injection delimiters, and graceful adapter failure fallback.
  - Added controlled gateway schema names for analysis, equivalence, solutions, tests, explanations, and slide decks. Gateway Pydantic validation remains mandatory; Ollama receives the corresponding JSON schema through LangChain `format`.
  - Added safe retrieval trace API data and a compact frontend provenance panel that distinguishes reuse, adaptation, related grounding, external discovery, and fresh generation while describing verification as bounded testing rather than proof.
  - Validation passed: 30 backend tests, 9 gateway tests, 1 sandbox test, slide-renderer fixture test, frontend TypeScript/Vite production build, Compose validation, existing/empty database migrations, backfill dry run, two actual idempotency backfill passes, reconciliation dry run, `git diff --check`, and live direct/same-origin health. Two additional isolated reuse/promotion gate tests were added afterward and passed static syntax validation, but their final Docker rerun was blocked by the approval quota. Backfill converged on 1 canonical problem, 1 variant, 1 verified solution, and 10 reusable asserting tests; reconciliation reported zero missing/orphaned/mismatched points. No paid/quota-limited inference request was used for validation.
- Generated solution descriptive-field widening on 2026-07-12:
  - Root cause of `StringDataRightTruncation` was direct persistence of model-generated `algorithm_pattern`, `time_complexity`, and `space_complexity` into `VARCHAR(120)` columns.
  - Changed those fields to SQLAlchemy `Text` for both job-scoped `GeneratedSolution` and corpus `ReusableSolution`; widening the reusable table prevents the same value from failing later during promotion.
  - Added forward migration `0003_widen_solution_fields` after `0002_retrieval_corpus`. Upgrade widens six descriptive columns to PostgreSQL `TEXT`; downgrade explicitly truncates to 120 characters before restoring `VARCHAR(120)`.
  - Added application quality bounds of 300 characters for algorithm-pattern names and 1,000 characters for time/space descriptions. Normalization collapses whitespace, rejects blanks, warns on excessive output, and conservatively bounds it without using database limits as validation.
  - Solution, ladder, variant, adaptation, and repair paths now share normalization. Prompts request concise algorithm names and Big-O plus at most one explanatory sentence.
  - Generated-solution persistence now flushes each candidate inside the shared transaction and logs only approach plus field lengths. Pipeline failure handling already rolls back before querying/updating the failed job. `VerificationRun.status` remains authoritative; `GeneratedSolution.verification_status` is a transactionally updated current-status cache.
  - Added SQLAlchemy type tests, PostgreSQL long-value integration coverage, normalization regressions, and transaction-recovery coverage. Static validation passed for 82 backend Python files, `git diff --check` passed, and direct normalization regression checks passed.
  - Live validation completed after Docker resumed: Alembic reports `0003_widen_solution_fields` at head with no pending schema operations, long descriptive fields persist successfully, the backend suite reports 40 passed and 1 skipped, Compose validation passes, and a fresh-database `0001 -> 0002 -> 0003` migration plus PostgreSQL persistence regression passed.
- Sudoku asserting-test stabilization on 2026-07-12:
  - Job `d9558ea6-05e8-4a15-8829-57c2134de54a` failed because model-generated Sudoku tests included malformed boards and ambiguous puzzles whose valid solution could differ from an exact expected grid.
  - Added deterministic Sudoku test normalization that validates a known puzzle/solution pair and derives ten uniquely constrained exact-output cases using `.` for empty cells.
  - Fixed problem detection to key on Sudoku semantics instead of requiring the literal token `9x9`; the supplied statement expresses the dimensions through constraints and therefore bypassed the original trigger.
  - The exact failed job was rerun successfully to `COMPLETED`: its solution variants passed all 10 asserting tests, explanation and slide artifacts were generated, retrieval verification reports `PASSED`, and final backend, Alembic, Compose, and diff checks passed.
- Structured verification and beginner-first explanation pivot on 2026-07-12:
  - Combination Sum job `0080c749-96cc-478e-9652-f5d301a06f11` exposed a semantically invalid generated assertion: candidates `2,5`, target `10` incorrectly expected a combination containing `3`. Test JSON was structurally valid but the prior gateway schema used untyped dictionaries and could not reject it.
  - LangChain now requests provider-native Pydantic structured output for approved schemas, with strict typed test objects and a validated JSON-mode fallback when a provider rejects native schemas. Combination Sum assertions are recomputed by a deterministic oracle using the selected solution's one-line or two-line stdin contract.
  - Slide generation was removed from fresh and exact-reuse pipelines, the frontend result controls, gateway schema list, backend status progression, environment configuration, and Docker Compose. Historical slide database/API fields remain readable for backward compatibility but no new slide artifacts are produced.
  - Explanation generation now makes one structured request per verified solution and combines the lessons under approach headings. Each lesson teaches prerequisites, data-structure operations, intuition, state variables, execution flow, dry run, code mapping, correctness, complexity derivation, and pitfalls for a beginner.
  - Live validation passed: backend 42 passed and 1 skipped, gateway 11 passed, frontend TypeScript passed, Compose configuration and diff checks passed. The exact Combination Sum job completed with BRUTE_FORCE, IMPROVED, and OPTIMAL all passing 12 tests, three detailed explanation sections, and zero slide artifacts.
- Unified deep walkthrough on 2026-07-12:
  - Removed the inferred illustration cards, Markdown-table-to-card conversion, SVG export, and separate illustration section. These representations guessed structure from prose and could hide important control-flow details.
  - Replaced them with one per-approach deep walkthrough containing the original supplied example, an annotated code stub, a state-variable model, a micro-step execution table tied to code phases, recursive call/return or iteration flow, and an invariant-based explanation of why each decision is valid.
  - Explanation generation now receives the full original problem statement so it can trace the given example rather than relying on the short analyzer summary or silently inventing inputs.
  - Live Combination Sum exact-reuse validation completed with three passing solutions and a 6,013-character unified walkthrough containing all required sections for all three approaches. Backend tests remained at 42 passed and 1 skipped; frontend TypeScript produced no compiler errors.
- Code and test-result presentation hardening on 2026-07-14:
  - Generated Java is now normalized at the persistence boundary: Markdown fences are removed and minified Java is conservatively expanded into indented structural lines without splitting strings or `for (...)` headers. Exact verified-corpus reuse passes through the same normalizer.
  - Job `90c3ca5f-d0ff-4f94-bca3-dd64b77cb7b5` was rerun successfully. BRUTE_FORCE, IMPROVED, and OPTIMAL persisted as 36, 30, and 30 formatted lines respectively, and all passed 36 asserting tests.
  - The Tests view retains aggregate status/pass/fail/average metrics at the top and, after execution, presents each test's status, returned stdout value, stderr when present, and individual runtime beside its input and expected value.
  - Live UI verification confirmed 36 returned-value panels and 36 timing badges. The complete backend suite passed with 44 tests and 1 skip; frontend TypeScript passed.
  - Follow-up solution targeting added explicit per-approach selection to the Tests view. Stored verification metrics, interactive results, and execution code are scoped to the selected solution. The Explanation proof run now explicitly identifies and executes its currently selected explanation approach, clearing stale results whenever the selection changes.
