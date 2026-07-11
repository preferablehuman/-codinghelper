# Study Buddy Programming Explainer

Study Buddy is a programming explanation assistant. It accepts a programming or DSA problem, builds a grounded evidence pack, generates solutions through a provider-neutral model gateway, verifies code in a sandbox, and displays an interactive explanation.

## Architecture

The default project runs as seven Docker Compose services, with Ollama available as an optional eighth service:

- `frontend`: React, Vite, TypeScript, Tailwind UI
- `backend`: provider-neutral FastAPI orchestration, persistence, and RAG modules
- `model-gateway`: stable internal `/health` and `/generate` API with provider adapters
- `postgres`: relational state for jobs, results, metadata, history
- `qdrant`: vector database for source chunks and semantic retrieval
- `sandbox-runner`: isolated Python and Java code execution
- `slide-renderer`: markdown, HTML preview, and PowerPoint deck artifact generation
- `ollama` (optional): local GGUF model serving when the gateway is configured for Ollama

PostgreSQL is the application source of truth. Qdrant stores embeddings. The backend orchestrates jobs but has no Gemini/Ollama knowledge; all LLM calls cross the model-gateway API. Generated code only runs in `sandbox-runner`.

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

The code for `frontend`, `backend`, `model-gateway`, `sandbox-runner`, and `slide-renderer` is bind-mounted into their containers. Python services run with reload enabled, and Node services install dependencies into `./data/...` at startup.

## Quick Start

```powershell
cd "D:\Development\study buddy"
copy .env.example .env
docker compose up --build
```

After the first build, code changes can usually be picked up with:

```powershell
docker compose restart backend
docker compose restart model-gateway
docker compose restart sandbox-runner
docker compose restart slide-renderer
docker compose restart frontend
```

Open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/api/health
- Model gateway: internal-only at `http://model-gateway:8300`; inspect readiness through backend `/api/health`
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

## Model Gateway

The application talks only to `MODEL_GATEWAY_URL`. Provider selection, credentials, model names, retries, and provider-specific HTTP formats belong exclusively to `model-gateway`.

For Gemini, configure `.env`:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=your_key_from_google_ai_studio
```

Restart only the gateway after changing providers or keys:

```powershell
docker compose restart model-gateway
```

The credential is available only to the gateway container and is never included in the frontend bundle or normal API responses. Adding another provider requires one gateway adapter; the application backend, pipeline, and frontend contract remain unchanged.

The backend intentionally stays online when the model gateway is degraded. `/api/health` reports model readiness, while history and other non-generation features continue working. Provider failures therefore appear as explicit job/gateway errors instead of browser-level `Failed to fetch` messages.

The frontend sends `/api` requests to its own origin and Vite proxies them internally to `backend:8000`. This avoids browser coupling to `localhost:8000` and works when the UI is opened from another device on the network.

The solution ladder is generated as separate structured requests for brute-force, optional improved, and optimal implementations. This prevents a truncated combined response from silently producing only one approach.

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
