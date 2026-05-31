# Docker Deployment

This template is designed to start on one 2 vCPU / 4GB RAM server. The service
boundary still stays clean: only the API touches SQLite, and the runner talks to
the API over REST.

## Production Topology

```text
Internet
  |
  v
web container: Nginx on WEB_PORT
  - serves React static files
  - proxies /api/* to api:8000
  |
  +--> api container: FastAPI
        - owns /data/app.db
        - creates schema and seeds roles/admin on startup
        - exposes runner claim/complete/fail endpoints
        |
        +--> sqlite_data named volume

runner container
  - does not mount SQLite
  - polls http://api:8000/api/runner/*
  - runs Hermes Agent as the embedded agent runtime
```

## First Deploy

Run from the repository root:

```bash
cp .env.docker.example .env
```

Edit `.env` before starting:

- `SECRET_KEY`: long random application secret.
- `RUNNER_API_KEY`: long random key shared by API and runner.
- `DEFAULT_ADMIN_PASSWORD`: strong initial admin password.
- `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `HERMES_API_KEY` for Hermes Agent model access.
- `APP_VERSION`: Docker image tag and runtime version label. Keep it aligned with `VERSION`.
- `WEB_PORT`: usually `80`, or `8080` when another reverse proxy owns port 80.

Start the stack:

```bash
./scripts/docker-deploy.sh
```

Equivalent raw command:

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --build
```

Check health:

```bash
docker compose --env-file .env -f infra/docker-compose.yml ps
curl http://127.0.0.1:${WEB_PORT:-80}/health
curl http://127.0.0.1:${WEB_PORT:-80}/api/health
```

After first login as the seeded admin, open the admin console settings page and save the Hermes runtime config. The API stores that config in SQLite; the runner reads it from `/api/runner/config/hermes` every time the runner process starts.

## 4GB Server Defaults

The default `.env.docker.example` memory caps are conservative:

```text
web:    128m
api:    768m
runner: 1536m
```

That leaves memory for the OS, Docker, disk cache, Nginx buffering, and temporary
deployment spikes. Keep `API_WORKERS=1` initially. Increase to `2` only after
measuring real API latency and SQLite write contention.

For the runner, start with:

```text
RUNNER_MAX_CONCURRENCY=1
```

Use `RUNNER_MAX_CONCURRENCY=1` for the first Hermes Agent rollout. Raise
concurrency only after measuring memory, tool latency, provider rate limits, and
job heartbeat behavior.

## Web/API Origin

The Docker default uses same-origin requests:

```text
VITE_API_BASE_URL=
```

In that mode, the browser calls `/api/...`, and Nginx forwards those requests to
`api:8000`.

Only set `VITE_API_BASE_URL=https://api.example.com` when API and web are on
separate public origins. Because Vite embeds this value at build time, rebuild
the web image after changing it:

```bash
docker compose --env-file .env -f infra/docker-compose.yml build web
docker compose --env-file .env -f infra/docker-compose.yml up -d web
```

## SQLite Persistence And Backup

SQLite lives in the Docker named volume `sqlite_data` at `/data/app.db` inside
the API container. The runner must never mount this volume.

Create an online backup:

```bash
./scripts/docker-backup-sqlite.sh
```

The script writes backups under `/data/backups` inside the same named volume.
Copy backups off-server regularly with your normal backup agent or object storage
sync.

## Upgrade

```bash
git pull
docker compose --env-file .env -f infra/docker-compose.yml build
docker compose --env-file .env -f infra/docker-compose.yml up -d
docker compose --env-file .env -f infra/docker-compose.yml ps
```

Create a SQLite backup before upgrades that touch schema or task execution.

## Scaling Path

Keep one server until one of these is true:

- runner queues stay high even after increasing `RUNNER_MAX_CONCURRENCY`;
- API latency is high while CPU is saturated;
- SQLite writes frequently block;
- you need high availability or isolated untrusted task execution.

The first split should be the runner. Deploy another runner container on a
separate host with:

```text
RUNNER_API_BASE_URL=https://your-domain.example.com
RUNNER_API_KEY=the-same-runner-key
RUNNER_NAME=runner-02
```

Do not split SQLite onto shared network storage. If the database needs to move,
move it with the API service or migrate the API persistence layer to a server
database.
