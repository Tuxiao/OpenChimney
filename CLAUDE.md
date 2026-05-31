# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read this first

`.codex/project-memory.md` is the project-local memory for coding agents: current
architecture decisions, module-by-module notes, verified commands, and boundary
rules. Read it before non-trivial changes. This file is the condensed, command-
oriented companion to it.

## What this is

OpenChimney (package name `sqlite-service-kit`) is an AI-service scaffold that
turns an agent Skill into a small multi-user web service. Three apps:

- `apps/api` — FastAPI + SQLAlchemy backend that **owns SQLite**. Auth, members,
  orders, tasks, conversations, admin, and the runner-facing REST endpoints.
- `apps/runner` — independent Python worker that polls the API over REST and runs
  `ai.agent.v1` jobs via Hermes Agent. **Never touches SQLite.**
- `apps/web` — React + Vite + TypeScript SPA: public landing/pricing, local auth,
  user console (`/console`), super admin console (`/admin`).

Data flow: user creates a task / posts a task message → API stores it in SQLite
and enqueues a `RunnerJob` → runner claims it over REST, executes via Hermes →
runner reports `complete`/`fail` → API writes the assistant reply back into the
conversation and updates task state.

## Non-negotiable boundaries

These are load-bearing; violating them breaks the security model. Do not "fix"
them without an explicit migration task.

- **Only `apps/api` reads or writes SQLite.** Never give `apps/runner` a database
  path, `DATABASE_URL`, or the `sqlite_data` volume mount.
- The runner talks to the API **only** over REST, authenticated with
  `X-Runner-Key`, in this lifecycle: `config → heartbeat → claim → job heartbeat
  → complete/fail`.
- Browser production calls go **same-origin** through `/api` (Nginx proxy). Only
  use a split `VITE_API_BASE_URL` when web and API are on separate public origins.
- `ai.agent.v1` is the primary job protocol; keep legacy `ai.chat` compatibility
  unless removal is the explicit task.
- Keep Hermes toolsets behind an explicit whitelist. Do **not** enable `terminal`,
  `file`, or broad browser/file-write toolsets by default. Default allowed:
  `safe`, `web`, `search`, `vision`, `image_gen`, `mcp-sqlite-service`.

## Toolchain

- Python apps (`api`, `runner`) use **`uv`** — always prefix Python commands with
  `uv run`. `apps/api` needs Python ≥3.9; `apps/runner` needs ≥3.11.
- Only `apps/web` is an npm workspace (declared in the root `package.json`); the
  Python apps are managed via their own `pyproject.toml` + `uv.lock`.
- The runner depends on `hermes-agent` pinned to a git tag — installs pull from
  GitHub.

## Commands

### Full verification before handing back changes
```bash
cd apps/api && uv run pytest
cd apps/runner && uv run pytest
cd apps/web && npm test
cd apps/web && npm run build
docker compose --env-file .env -f infra/docker-compose.yml config
```

### Run a single test
```bash
# API (pytest; cwd must be apps/api)
cd apps/api && uv run pytest tests/test_auth.py::test_name -v

# Runner (pytest-asyncio, asyncio_mode=auto)
cd apps/runner && uv run pytest tests/test_worker.py::test_name -v

# Web (vitest — filter by filename or by -t "test name")
cd apps/web && npm test -- App          # files matching "App"
cd apps/web && npm test -- -t "renders" # tests whose name matches
```

### Local dev servers
```bash
cd apps/api    && uv run uvicorn app.main:app --reload --port 8000
cd apps/web    && npm install && npm run dev          # http://127.0.0.1:5173
cd apps/runner && uv run sqlite-service-runner run     # also: once | config
```
URLs: API health `http://127.0.0.1:8000/api/health`; web dev `:5173`.

### Build / type-check
`cd apps/web && npm run build` runs `tsc --noEmit` (the type-check gate) then
`vite build`. `apps/api` is configured for `ruff` (line-length 100) but ruff is
not a declared dependency — run it ad hoc with `uvx ruff check apps/api` if needed.

### Docker stack
```bash
cp .env.docker.example .env       # then edit secrets (see below)
./scripts/docker-deploy.sh        # = docker compose --env-file .env -f infra/docker-compose.yml up -d --build
./scripts/docker-backup-sqlite.sh # SQLite backup
```
Three services: `web` (Nginx, `${WEB_PORT:-80}`, proxies `/api` → `api:8000`),
`api` (FastAPI on 8000, owns `/data/app.db` on the `sqlite_data` volume),
`runner` (no public port, no DB mount). After changing Hermes settings in the
admin console, **restart the runner** so it refetches DB-backed config:
`docker compose --env-file .env -f infra/docker-compose.yml restart runner`.

## Versioning

`VERSION` (repo root) is the single source of truth. After editing it, run
`npm run version:sync` to propagate into the two `package.json`s + lockfiles, both
`pyproject.toml`s, `apps/runner/app/__init__.py`, `apps/api/app/version.py`,
`apps/web/src/version.ts`, and the `.env*.example` `APP_VERSION` values. Verify
with `npm run version:check` (fails if anything is out of sync). The API serves
the running version at `GET /api/version` and `GET /api/health`; the runner
includes it in its heartbeat. Do **not** hand-edit individual version constants.

## Configuration notes

- API config is parsed in `apps/api/app/config.py` (`AppConfig.from_env`). Key env
  vars: `DATABASE_URL`, `RUNNER_KEY` (falls back to `RUNNER_API_KEY`),
  `CORS_ORIGINS`, `SESSION_TTL_SECONDS`, `CREATE_SCHEMA_ON_STARTUP`,
  `SEED_ON_STARTUP`, and the seeded `DEFAULT_ADMIN_*` / `SUPER_ADMIN_*` accounts.
- The runner key must match between API (`RUNNER_API_KEY`) and runner
  (`RUNNER_API_KEY`). Before exposing the stack, replace `SECRET_KEY`,
  `RUNNER_API_KEY`, `DEFAULT_ADMIN_PASSWORD`, `SUPER_ADMIN_PASSWORD`, and the
  Hermes/provider API keys.
- Web API client (`apps/web/src/lib/apiClient.ts`): empty `VITE_API_BASE_URL` in
  local dev falls back to **mock data** (`src/data/mockData.ts`); `VITE_API_MOCKS=1`
  forces mocks. In Docker keep it empty for same-origin calls.

## High-signal entry points

```
apps/api/app/main.py            FastAPI factory, CORS, router mounting, /api/health
apps/api/app/models.py          SQLAlchemy schema (users, tasks, conversations, runner jobs, audit, settings)
apps/api/app/migrations.py      Schema creation + seed (roles, admin, super admin, Hermes config)
apps/api/app/hermes_settings.py default / merged / public / runner Hermes config helpers
apps/api/app/routers/tasks.py   Task CRUD + task-message → ai.agent.v1 enqueue path
apps/api/app/routers/runner.py  config, heartbeat, claim, job heartbeat, complete, fail
apps/runner/app/worker.py       Polling loop, heartbeats, completion/failure, backoff
apps/runner/app/providers.py    ProviderRegistry, HermesAgentRuntime, ChatProviderStub
apps/web/src/App.tsx            All routes: public pages, auth, user + admin consoles
apps/web/src/types/domain.ts    Frontend domain types (incl. Hermes config)
infra/docker-compose.yml        Service boundary and volume mounts
```

Deeper docs live in `docs/` (`architecture.md`, `api.md`, `runner.md`,
`frontend.md`, `deployment.md`).
