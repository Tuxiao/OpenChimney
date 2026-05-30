# Runner Deployment Notes

The runner is an independently deployable Python service in `apps/runner`. It never reads SQLite directly and communicates with the API only through REST endpoints authenticated by `X-Runner-Key`. The first production agent runtime is Hermes Agent, embedded as a Python library inside the runner process.

Recommended deployment model:

1. Deploy the API and SQLite database on the application server.
2. Deploy `apps/runner` as a separate process or container. It can run on the same 4GB server at first.
3. Set `RUNNER_API_BASE_URL` to the internal API URL in Docker (`http://api:8000`) or to the public/private API URL when the runner is on another host.
4. Set `RUNNER_KEY` or `RUNNER_API_KEY` to the same secret configured by the API.
5. Configure Hermes from the admin console settings page. Those settings are stored in SQLite and exposed to the runner through `POST /api/runner/config/hermes`.
6. Set one Hermes provider key, such as `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or the dedicated `HERMES_API_KEY` fallback.
7. Start `sqlite-service-runner run` under systemd, Docker, or another process manager.

Default API prefix is `/api/runner`; override with `RUNNER_API_PREFIX` if the API routes differ.

On startup, `sqlite-service-runner run` and `sqlite-service-runner once` fetch the Hermes config from the API before constructing the worker. The fetched config controls `model`, `provider`, `base_url`, `api_key`, `task_root`, `hermes_home`, toolsets, memory mode, timeout, and max iterations. Environment variables are fallback values when the database config omits a field.

Every Hermes job gets an initialized workspace below `task_root`. The runner uses `workspace_id` when present, otherwise `task-<task_id>`, then `conversation-<conversation_id>`, then `job-<job_id>`. Initialization creates `.hermes.md`, `AGENTS.md`, `workspace.json`, `artifacts/`, `logs/`, and `tmp/`.

Resume is enabled by default. The API-created task jobs include `session_id=conversation-<conversation_id>` and `workspace_id=task-<task_id>`, so follow-up messages in the same task conversation reuse the same Hermes session and task directory. Payloads can set `"resume": false` to force a job-scoped session.

Default runner capabilities are `ai.agent.v1,ai.chat`. `ai.agent.v1` jobs execute through Hermes; legacy `ai.chat` jobs are mapped to a restricted Hermes chat task. Keep `terminal`, `file`, and `browser` toolsets disabled unless the job type has a separate sandbox and approval policy.

See `apps/runner/README.md` for the full environment variable list, REST payload contract, and a systemd unit example.
