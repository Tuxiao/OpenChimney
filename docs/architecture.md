# Architecture

SQLite Service Kit is a single-owner SQLite architecture:

- `apps/api` is the only process that reads or writes SQLite.
- `apps/web` talks to the API with JSON REST endpoints.
- `apps/runner` is deployed separately and communicates only through REST.

This keeps SQLite deployment simple while still allowing the runner to live on a
different VPS or worker server.

## Data Ownership

The API owns:

- users, sessions, roles, members
- orders and order items
- tasks, conversations, messages, attachments
- runner nodes, runner jobs, job events
- audit logs and app settings

The runner owns no database state. It keeps only in-memory loop state and uses
API idempotency to report job progress. AI jobs execute through an embedded
Hermes Agent runtime with per-job workspaces and whitelisted toolsets.

## Runner Protocol

The runner authenticates with `X-Runner-Key`.

1. `POST /api/runner/heartbeat`
2. `POST /api/runner/jobs/claim`
3. Execute the returned job payload.
4. `POST /api/runner/jobs/{id}/heartbeat` while work is active.
5. `POST /api/runner/jobs/{id}/complete` or `POST /api/runner/jobs/{id}/fail`.

The API handles leases in SQLite transactions. A job can be claimed only when it
is queued or retryable, available now, and not currently leased.

## Deployment Shape

```text
Single server default
  web container
    Nginx serves React and proxies /api to api:8000
  api container
    FastAPI owns SQLite on sqlite_data volume
  runner container
    polls http://api:8000/api/runner
```

The runner can move to another server later by setting
`RUNNER_API_BASE_URL=https://your-domain.example.com`. Do not mount the SQLite
database into the runner host.
