# SQLite Service Kit Runner

Independent Python task runner for SQLite Service Kit. The runner never opens or reads SQLite directly. It talks only to the API over HTTP, authenticating every request with `X-Runner-Key`.

## Responsibilities

- send runner heartbeat
- poll and claim jobs
- renew claimed job heartbeat while work is running
- execute Hermes Agent jobs for `ai.agent.v1` and legacy `ai.chat`
- complete jobs with assistant message/result payloads
- fail jobs with structured retryable or non-retryable error payloads

## Install

```bash
cd apps/runner
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

## Configure

Required:

```bash
export RUNNER_API_BASE_URL="https://api.example.com"
export RUNNER_KEY="replace-with-shared-runner-secret"
# RUNNER_API_KEY is also accepted for compatibility with the root .env file.
```

Optional:

```bash
export RUNNER_ID="runner-vps-1"
export RUNNER_API_PREFIX="/api/runner"
export RUNNER_CAPABILITIES="ai.agent.v1,ai.chat"
export RUNNER_AGENT_RUNTIME="hermes"
export RUNNER_POLL_INTERVAL_SECONDS="2"
export RUNNER_EMPTY_POLL_INTERVAL_SECONDS="5"
export RUNNER_HEARTBEAT_INTERVAL_SECONDS="30"
export RUNNER_JOB_HEARTBEAT_INTERVAL_SECONDS="10"
export RUNNER_REQUEST_TIMEOUT_SECONDS="15"
export RUNNER_MAX_BACKOFF_SECONDS="60"
export RUNNER_LOG_LEVEL="INFO"
export HERMES_MODEL="anthropic/claude-sonnet-4.6"
export HERMES_PROVIDER="anthropic"
export HERMES_BASE_URL=""
export HERMES_API_KEY=""
export HERMES_HOME="/runner/.hermes"
export HERMES_WORKSPACE_ROOT="/runner/workspaces"
export HERMES_MAX_ITERATIONS="20"
export HERMES_DEFAULT_TOOLSETS="safe"
export HERMES_ALLOWED_TOOLSETS="safe,web,search,vision,image_gen,mcp-sqlite-service"
export HERMES_MEMORY_MODE="tenant"
export HERMES_TIMEOUT_SECONDS="300"
```

Hermes Agent needs a configured model provider. The preferred path is the admin
console Hermes settings page, which stores model, provider, base URL, task root,
Hermes home, toolsets, and optional API key in SQLite. On `run` and `once`, the
runner first calls `POST /api/runner/config/hermes`, then initializes Hermes from
that database-backed config. Environment variables remain startup fallbacks.

Each Hermes job is initialized in a dedicated workspace under the configured
task root. The runner prefers stable task directories such as
`/runner/workspaces/task-123`; if a task id is unavailable, it falls back to
`conversation-<id>` and then `job-<id>`. Workspace initialization creates
`.hermes.md`, `AGENTS.md`, `workspace.json`, `artifacts/`, `logs/`, and `tmp/`.

Conversation resume is enabled by default. Jobs with the same conversation id
use the same Hermes `session_id` (`conversation-<id>`), and task jobs use a
stable Hermes `task_id` (`task-<id>`). Payloads may override this with
`session_id`, `workspace_id`, `parent_session_id`, or `"resume": false`.

You can also set one of `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, or
`OPENAI_API_KEY` according to the model/provider you use.

## Run

```bash
sqlite-service-runner config
sqlite-service-runner once
sqlite-service-runner run
```

`once` exits with code `0` after a job is processed and `3` when no job is available.

## REST Contract

All requests are `POST` and include:

```http
X-Runner-Key: <RUNNER_KEY>
Content-Type: application/json
Accept: application/json
```

Default endpoint prefix: `/api/runner`

### Hermes Runtime Config

`POST /api/runner/config/hermes`

```json
{
  "runner_id": "runner-vps-1"
}
```

Response includes the runtime settings the runner applies at startup:

```json
{
  "enabled": true,
  "model": "anthropic/claude-sonnet-4.6",
  "provider": "anthropic",
  "base_url": null,
  "api_key": null,
  "task_root": "/runner/workspaces",
  "hermes_home": "/runner/.hermes",
  "max_iterations": 20,
  "default_toolsets": ["safe"],
  "allowed_toolsets": ["safe", "web"],
  "memory_mode": "tenant",
  "timeout_seconds": 300
}
```

### Runner Heartbeat

`POST /api/runner/heartbeat`

```json
{
  "runner_id": "runner-vps-1",
  "status": "idle",
  "capabilities": ["ai.agent.v1", "ai.chat"]
}
```

### Claim Job

`POST /api/runner/jobs/claim`

```json
{
  "runner_id": "runner-vps-1",
  "capabilities": ["ai.agent.v1", "ai.chat"]
}
```

No job response may be `204`, `null`, or `{"job": null}`.

Claimed job response:

```json
{
  "job": {
    "id": "job_123",
    "type": "ai.agent.v1",
    "payload": {
      "runtime": "hermes",
      "task_kind": "ai.chat",
      "instruction": "Reply to the latest user message in this task conversation.",
      "workspace_id": "task-123",
      "session_id": "conversation-456",
      "resume": true,
      "messages": [
        {"role": "user", "content": "Hello"}
      ],
      "toolsets": [],
      "output_schema": "assistant_message.v1"
    },
    "attempt": 1
  }
}
```

The client also accepts `job_id`/`task_id` and `job_type`/`task_type` aliases.

### Job Heartbeat

`POST /api/runner/jobs/{job_id}/heartbeat`

```json
{
  "runner_id": "runner-vps-1"
}
```

### Complete Job

`POST /api/runner/jobs/{job_id}/complete`

```json
{
  "runner_id": "runner-vps-1",
  "result": {
    "provider": "hermes",
    "runtime": "hermes-agent",
    "model": "anthropic/claude-sonnet-4.6",
    "assistant_message": {
      "role": "assistant",
      "content": "Hello. How can I help?"
    },
    "messages": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hello. How can I help?"}
    ],
    "artifacts": [],
    "usage": {},
    "metadata": {
      "task_kind": "ai.chat",
      "toolsets": [],
      "iterations": 0,
      "workspace_id": "task-123",
      "session_id": "conversation-456",
      "task_ref": "task-123",
      "resume": true
    }
  }
}
```

### Fail Job

`POST /api/runner/jobs/{job_id}/fail`

```json
{
  "runner_id": "runner-vps-1",
  "error": {
    "code": "runner_execution_error",
    "message": "temporary outage",
    "retryable": true,
    "details": {
      "exception_type": "RuntimeError"
    }
  }
}
```

## Separate VPS Deployment

Create a service account and install only this runner package on the worker machine. The worker needs outbound network access to the API and does not need database credentials or filesystem access to the API server.

Example systemd unit:

```ini
[Unit]
Description=SQLite Service Kit Runner
After=network-online.target
Wants=network-online.target

[Service]
User=runner
WorkingDirectory=/opt/sqlite-service-kit/apps/runner
Environment=RUNNER_API_BASE_URL=https://api.example.com
Environment=RUNNER_KEY=replace-with-shared-runner-secret
Environment=RUNNER_ID=runner-vps-1
Environment=RUNNER_API_PREFIX=/api/runner
Environment=RUNNER_AGENT_RUNTIME=hermes
Environment=RUNNER_CAPABILITIES=ai.agent.v1,ai.chat
Environment=HERMES_MODEL=anthropic/claude-sonnet-4.6
Environment=HERMES_HOME=/opt/sqlite-service-kit/apps/runner/.hermes
Environment=HERMES_MAX_ITERATIONS=20
Environment=HERMES_DEFAULT_TOOLSETS=safe
Environment=HERMES_MEMORY_MODE=tenant
Environment=HERMES_TIMEOUT_SECONDS=300
Environment=RUNNER_LOG_LEVEL=INFO
ExecStart=/opt/sqlite-service-kit/apps/runner/.venv/bin/sqlite-service-runner run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Test

```bash
cd apps/runner
pytest
```
