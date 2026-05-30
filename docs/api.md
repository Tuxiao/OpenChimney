# API Backend

FastAPI backend template for OpenChimney.

## Run Locally

```bash
cd apps/api
python3 -m pip install -e ".[test]"
uvicorn app.main:app --reload
```

Default runtime settings:

- `DATABASE_URL=sqlite:///./data/api.sqlite3`
- `RUNNER_KEY=dev-runner-key` or `RUNNER_API_KEY=dev-runner-key`
- `DEFAULT_ADMIN_EMAIL=admin@example.com`
- `DEFAULT_ADMIN_PASSWORD=admin1234`

The app enables SQLite `foreign_keys`, `busy_timeout=5000`, and WAL mode on
each connection. On startup it creates the schema and seeds `user`/`admin`
roles, the default admin account, and baseline app settings.

## Main Endpoints

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- `POST /api/auth/phone/request-code` returns a development SMS code for copy/paste testing
- `POST /api/auth/phone/verify-code` verifies the code and auto-registers first-time phone users
- `POST /api/auth/phone/login` signs in phone users after a password has been set
- `POST /api/auth/set-password` sets the password for the authenticated phone account
- `GET/POST/PATCH/DELETE /api/members`
- `GET/POST/PATCH /api/orders`
- `GET/POST/PATCH /api/tasks`
- `POST /api/tasks/{id}/messages` creates a task message and enqueues an `ai.agent.v1` runner job with `workspace_id=task-<id>`, `session_id=conversation-<id>`, and `resume=true`
- `GET/POST/PATCH /api/conversations`, `POST /api/conversations/{id}/messages`
- `GET /api/admin/overview`, `GET /api/admin/runner-jobs`
- `GET/PUT /api/admin/hermes-config` reads and saves the database-backed Hermes runner config
- `POST /api/runner/config/hermes` returns Hermes config to the runner, including the optional secret API key
- `POST /api/runner/heartbeat`
- `POST /api/runner/jobs/claim` for the independent runner wire format
- `POST /api/runner/claim` for batch-compatible internal/admin tooling
- `POST /api/runner/jobs/{id}/heartbeat`
- `POST /api/runner/jobs/{id}/complete`
- `POST /api/runner/jobs/{id}/fail`

Runner endpoints require `X-Runner-Key`. User/admin endpoints use
`Authorization: Bearer <token>` returned by register, login, or phone login.

Phone auth is intentionally development-friendly in this template: the SMS code
is stored hashed in SQLite and the response includes `dev_code` so the frontend
can show it to the user for copy/paste. A production app should replace that
response field with a real SMS provider dispatch.

## Tests

```bash
cd apps/api
pytest
```
