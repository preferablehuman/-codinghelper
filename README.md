# Study Buddy Programming Explainer

Study Buddy is a local-first programming explanation assistant. It accepts a programming or DSA problem, builds a grounded evidence pack from approved sources, generates a solution with a local model runtime, verifies code in a sandbox, and displays an explanation with slide markdown.

## Architecture

The project runs as seven Docker Compose services:

- `frontend`: React, Vite, TypeScript, Tailwind UI
- `backend`: FastAPI orchestration, PostgreSQL persistence, RAG modules, model-runtime client
- `ollama`: local GGUF model serving with GPU access
- `postgres`: relational state for jobs, results, metadata, history
- `qdrant`: vector database for source chunks and semantic retrieval
- `sandbox-runner`: isolated Python and Java code execution
- `slide-renderer`: markdown, HTML preview, and PowerPoint deck artifact generation

PostgreSQL is the application source of truth. Qdrant stores embeddings. The backend orchestrates everything. Generated code only runs in `sandbox-runner`.

## Local Data And Live Code Mounts

All persistent container data is directed into `./data`:

- `data/postgres`: PostgreSQL cluster data
- `data/qdrant`: Qdrant vector storage
- `data/backend/artifacts`: backend generated artifacts
- `data/backend/model-cache`: local model files
- `data/backend/source-cache`: source cache
- `data/ollama`: persistent Ollama model store
- `data/frontend/node_modules` and `data/frontend/npm-cache`: frontend dependency/runtime cache
- `data/sandbox-runner/work`: temporary generated-code execution work area, cleaned per run
- `data/slide-renderer/generated-slides`, `data/slide-renderer/node_modules`, and `data/slide-renderer/npm-cache`: slide artifacts and Node cache

The code for `frontend`, `backend`, `sandbox-runner`, and `slide-renderer` is bind-mounted into their containers. Backend and sandbox services run with reload enabled, and Node services install dependencies into `./data/...` at startup. Code-only edits should only require restarting the affected container, not rebuilding its image.

## Quick Start

```powershell
cd "D:\Development\study buddy"
copy .env.example .env
docker compose up --build
```

After the first build, code changes can usually be picked up with:

```powershell
docker compose restart backend
docker compose restart sandbox-runner
docker compose restart slide-renderer
docker compose restart frontend
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Ollama API: http://localhost:11434
- Sandbox health: http://localhost:8100/health
- Slide renderer health: http://localhost:8200/health
- Qdrant: http://localhost:6333

## Developer Commands

```powershell
make up
make down
make logs
make migrate
make test-backend
make test-sandbox
```

On Windows without `make`, run the equivalent Docker Compose commands from the `Makefile`.

## Logging

Every service writes logs to the console and to `./logs/<service>/` on the host:

- `logs/frontend/frontend.log`
- `logs/backend/backend.log`
- `logs/backend/backend-console.log`
- `logs/ollama/ollama.log`
- `logs/postgres/postgres.log`
- `logs/qdrant/qdrant.log`
- `logs/sandbox-runner/sandbox-runner.log`
- `logs/sandbox-runner/sandbox-runner-console.log`
- `logs/slide-renderer/slide-renderer.log`

File logs rotate at `LOG_MAX_BYTES=10485760` and keep `LOG_MAX_FILES=10` files total by default. Docker console logs are also capped at 10 files of 10 MB per service.

Set `VERBOSE_LOGGING=true` in `.env` before starting Compose to enable debug-level app logs and more detailed service output. PostgreSQL and Qdrant can be tuned further with `POSTGRES_LOG_*` and `QDRANT_LOG_LEVEL` in `.env`.

## Model Setup

The active generation runtime is Ollama. The backend talks to the Ollama HTTP API and keeps the older Hugging Face Transformers implementation in `backend/app/model_runtime/transformers_runtime.py` as an unused alternate path.

Selected defaults:

- Active generation model: `qwen2.5-coder:7b` through Ollama
- Quantization: Ollama `Q4_K_M`
- Installed model size: about 4.7 GB
- Configured context: `OLLAMA_NUM_CTX=8192`
- Retrieval embedding model: [`BAAI/bge-m3`](https://huggingface.co/BAAI/bge-m3)

The first Ollama startup pulls the model once into `data/ollama`, then later starts reuse that mounted store. The backend does not lazy-load the model for the first job: it waits for the Ollama service to become healthy, sends a warmup generation request during FastAPI startup, and only reports startup complete after model preload succeeds.

Important runtime settings:

- `MODEL_PROVIDER=ollama` selects the Ollama runtime.
- `OLLAMA_MODEL=qwen2.5-coder:7b` controls the model pulled by the Ollama container and used by the backend.
- `OLLAMA_KEEP_ALIVE=-1` keeps the warmed model resident.
- `OLLAMA_REQUIRE_GPU=true` makes the Ollama container fail if NVIDIA tooling is unavailable or if `ollama ps` does not report GPU execution for the warmed model. Backend startup also fails if Ollama reports zero VRAM residency for the warmed model.
- `OLLAMA_NUM_CTX=8192` keeps useful context while avoiding an oversized KV cache on modest VRAM.
- `data/ollama` is mounted to `/root/.ollama`, so the model is not downloaded again on every container start.

The job pipeline calls the configured model runtime for solution generation, test generation, explanation generation, and slide markdown generation. If the model cannot load or returns malformed structured output, the job is marked failed instead of silently using a deterministic placeholder.

## Retrieval Knowledge Base

The app should not depend on the user providing URLs. Optional user URLs are accepted, but automatic retrieval starts from curated, approved sources:

- CP-Algorithms
- The Algorithms GitHub organization
- Official Python documentation
- Official Java documentation
- Stack Exchange and Codeforces APIs where adapters are implemented
- GeeksforGeeks only with the restricted snippet/citation policy

The retrieval layer should prefer open/cacheable sources and store only metadata/snippets for restricted sources.

## Project Working Guidelines

- Start every session by reading `PROJECT_MEMORY.md`.
- End every implementation session by updating `PROJECT_MEMORY.md`.
- Prefer the simplest understandable implementation that satisfies the requirement.
- Touch only files directly required for the change.
- Ask when a product, hardware, data, or behavior choice materially affects the result and cannot be discovered from project context.
- Do not invent unsupported technical choices; document selected defaults and the reason for them.

## Limitations

- The system does not guarantee correctness.
- Online sources improve grounding but do not prove correctness.
- Verification depends on available and generated tests.
- LeetCode or paid platform scraping is not supported.
- GeeksforGeeks is handled with restricted retrieval rules.
- Local model quality depends on the configured model.
- Large models may require GPU and significant RAM or VRAM.
