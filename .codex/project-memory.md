# OpenChimney Project Memory

This file is project-local memory for coding agents working inside the
OpenChimney repository. Keep it public-safe: do not store secrets, personal
paths, local machine details, or private deployment notes here.

## System Overview

OpenChimney is an AI service engineering scaffold. It helps turn an agent Skill
into a small multi-user online service with public product pages, local auth, a
user console, a super admin console, FastAPI APIs, SQLite persistence, and an
independent REST-bound AI task runner.

Core boundary:

- The API is the only process that reads or writes SQLite.
- The runner never mounts SQLite and never receives database paths or database
  URLs.
- The runner communicates only through REST: config fetch, heartbeat, claim, job
  heartbeat, complete, and fail.
- Web uses same-origin `/api` behind Docker Nginx in production.
- AI work is represented as `ai.agent.v1` jobs. Legacy `ai.chat` compatibility
  is kept unless an explicit migration removes it.

Primary local URLs:

- Local API health: `http://127.0.0.1:8000/api/health`
- Local web dev: `http://127.0.0.1:5173`
- Docker web: `http://127.0.0.1:${WEB_PORT:-80}`
- Docker API health through web: `http://127.0.0.1:${WEB_PORT:-80}/api/health`

## Product Modules

### Public Product Surface

Path: `apps/web`

- Landing page explains the AI service scaffold, modules, REST runner boundary,
  and SQLite operations.
- Pricing page has Starter, Pro, and Team plans with CTAs into login.
- Product footer includes product, resource, deploy, company, security, terms,
  and contact links.

### Authentication

Implemented in `apps/api/app/routers/auth.py` and surfaced in
`apps/web/src/App.tsx`.

- Email/password login exists for the seeded admin account.
- Phone + SMS login auto-registers first-time phone users.
- Development SMS responses include `dev_code` for local copy/paste testing.
- Phone + password login works after a user sets a password.
- First phone login redirects to password setup when the account has no
  password.
- Authenticated frontend routes show user/admin navigation and sign out.

### User Console

Path: `apps/web/src/App.tsx`

- Task management page with filters, task table, selected task detail, runner
  events, and task-scoped chat entry.
- AI chat page for compact conversation work.
- User center page for local member/profile-style information.
- Account page for local account/security state.

### Super Admin Console

Path: `apps/web/src/App.tsx`

- Dashboard shows API health, SQLite status, runner polling state, failures,
  queue overview, audit stream, members preview, and orders preview.
- Members page previews member records.
- Orders page previews order records.
- Audit page shows recent account, runner, and database events.
- Settings page includes operational settings plus the Hermes agent runtime
  configuration form.

## Web App

Path: `apps/web`

Stack:

- React
- Vite
- TypeScript
- Tailwind
- lucide-react icons

Important files:

- `src/App.tsx`: route state, public pages, auth pages, user console, admin
  console, Hermes config UI.
- `src/lib/apiClient.ts`: FastAPI client and local mock fallback.
- `src/data/mockData.ts`: local mock state for dev/demo.
- `src/types/domain.ts`: frontend domain types, including Hermes config types.

API client behavior:

- In production Docker, `VITE_API_BASE_URL=` stays empty and the browser calls
  same-origin `/api/...`.
- In local dev, empty base URL uses mock data.
- Set `VITE_API_MOCKS=1` to force mock mode.
- Set `VITE_API_BASE_URL=https://api.example.com` only for split-origin
  deployments and rebuild the web image.

## API Backend

Path: `apps/api`

Stack:

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic

Important files:

- `app/main.py`: app factory, CORS, router mounting, `/api/health`.
- `app/config.py`: env config for SQLite path, runner key, CORS, session TTL,
  schema/seed flags, and default admin.
- `app/models.py`: users, roles, sessions, phone login codes, members, orders,
  order items, tasks, conversations, messages, attachments, runner nodes, runner
  jobs, runner job events, audit logs, and app settings.
- `app/migrations.py`: creates schema and seeds roles, admin account, baseline
  settings, and Hermes config.
- `app/hermes_settings.py`: default/merged/public/runner Hermes config helpers.
- `app/routers/auth.py`: email auth, phone auth, password setup, sessions.
- `app/routers/members.py`: member CRUD.
- `app/routers/orders.py`: order CRUD.
- `app/routers/tasks.py`: task CRUD and task-message-to-runner enqueue.
- `app/routers/conversations.py`: conversation/message CRUD scoped to user unless
  admin.
- `app/routers/admin.py`: overview, runner jobs, audit logs, Hermes config.
- `app/routers/runner.py`: runner config, heartbeat, claim, job heartbeat,
  complete, fail.

Runner job creation:

- `POST /api/tasks/{task_id}/messages` creates or reuses the task conversation.
- It enqueues a `RunnerJob` with `job_type="ai.agent.v1"`.
- Payload includes `runtime="hermes"`, `task_kind="ai.chat"`,
  `workspace_id="task-<task_id>"`, `session_id="conversation-<conversation_id>"`,
  and `resume=true`.
- Completion writes the assistant message back to the conversation and marks the
  task completed.

## Runner

Path: `apps/runner`

Executable: `sqlite-service-runner`

Core modules:

- `app/config.py`: env fallback config plus `with_hermes_settings()` for
  DB-backed Hermes config.
- `app/client.py`: REST client for config fetch, heartbeat, claim, job heartbeat,
  complete, and fail.
- `app/cli.py`: `run`, `once`, and `config`; `run` and `once` fetch Hermes
  config before constructing the worker.
- `app/worker.py`: polling loop, runner heartbeat, job heartbeat,
  completion/failure reporting, backoff.
- `app/providers.py`: `ProviderRegistry`, `HermesAgentRuntime`, and
  `ChatProviderStub` test fallback.

Runtime behavior:

- Default runtime is Hermes: `RUNNER_AGENT_RUNTIME=hermes`.
- Stub runtime is retained for tests and explicit fallback only.
- Runner startup calls `POST /api/runner/config/hermes`.
- Hermes is initialized with DB-backed `model`, `provider`, `base_url`,
  `api_key`, `task_root`, `hermes_home`, toolsets, memory mode, timeout, and max
  iterations.
- Hermes execution is wrapped with `asyncio.to_thread()` so the async worker can
  keep its existing heartbeat behavior.

Toolset policy:

- Prefer an explicit enabled toolset whitelist.
- Default allowed toolsets: `safe`, `web`, `search`, `vision`, `image_gen`,
  `mcp-sqlite-service`.
- Do not enable `terminal`, `file`, or broad browser/file-write capabilities by
  default.

## Docker Deployment

Important paths:

- `infra/docker-compose.yml`
- `apps/api/Dockerfile`
- `apps/web/Dockerfile`
- `apps/web/nginx.conf`
- `apps/runner/Dockerfile`
- `.env.docker.example`
- `scripts/docker-deploy.sh`
- `scripts/docker-backup-sqlite.sh`
- `docs/deployment.md`

Deployment shape:

- `web` uses Nginx, serves React static assets, exposes `WEB_PORT`, and proxies
  `/api/` to `api:8000`.
- `api` runs FastAPI on internal port `8000`, owns `/data/app.db`, and mounts
  `sqlite_data`.
- `runner` polls `http://api:8000/api/runner/*` internally and uses the same
  `RUNNER_API_KEY`.
- `runner` must not mount `sqlite_data`.
- Default 4GB-friendly memory caps: web 128 MB, API 768 MB, runner 1536 MB.
- `RUNNER_MAX_CONCURRENCY=1` is the conservative first rollout value.

## Verification Commands

Run these before handing back meaningful code changes:

```bash
cd apps/api && uv run pytest
cd apps/runner && uv run pytest
cd apps/web && npm test
cd apps/web && npm run build
docker compose --env-file .env -f infra/docker-compose.yml config
```

For deployment-affecting changes, also verify:

```bash
curl http://127.0.0.1:${WEB_PORT:-80}/health
curl http://127.0.0.1:${WEB_PORT:-80}/api/health
docker inspect infra-runner-1 --format '{{json .Mounts}}'
```

The runner mount inspection should show no SQLite volume mount.
