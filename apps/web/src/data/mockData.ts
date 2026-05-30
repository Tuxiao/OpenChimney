import type { AuditEvent, HealthSnapshot, HermesConfig, Member, Order, RunnerJob, Task } from "../types/domain";

export const tasks: Task[] = [
  {
    id: "TSK-1042",
    title: "Reconcile member import",
    owner: "Avery Chen",
    status: "running",
    priority: "high",
    runner: "runner-east-1",
    updatedAt: "09:42",
    details: "Validates uploaded member rows, normalizes local roles, and writes the accepted set into SQLite in a single transaction.",
    events: ["REST pull accepted", "42 rows parsed", "SQLite transaction open"]
  },
  {
    id: "TSK-1039",
    title: "Create invoice snapshots",
    owner: "Noah Kim",
    status: "queued",
    priority: "normal",
    runner: "unassigned",
    updatedAt: "09:31",
    details: "Generates order ledger snapshots for paid and pending orders. The runner claims this through the REST queue.",
    events: ["Queued by user console", "Awaiting runner poll"]
  },
  {
    id: "TSK-1033",
    title: "Hermes agent smoke test",
    owner: "Mira Patel",
    status: "blocked",
    priority: "normal",
    runner: "runner-local",
    updatedAt: "08:58",
    details: "Checks the Hermes-backed runner path while payment and notification providers stay mocked.",
    events: ["Hermes runtime returned 202", "Manual review requested"]
  },
  {
    id: "TSK-1028",
    title: "Archive old chat threads",
    owner: "Avery Chen",
    status: "done",
    priority: "low",
    runner: "runner-east-1",
    updatedAt: "Yesterday",
    details: "Moves resolved chat records into a compact archive table and keeps the latest user-visible summary.",
    events: ["Runner completed", "Audit event recorded"]
  }
];

export const runnerJobs: RunnerJob[] = [
  { id: "JOB-8801", taskId: "TSK-1042", endpoint: "POST /api/runner/jobs/claim", status: "running", attempt: 1, nextPollAt: "now" },
  { id: "JOB-8800", taskId: "TSK-1039", endpoint: "POST /api/runner/jobs/{id}/heartbeat", status: "queued", attempt: 0, nextPollAt: "09:45" },
  { id: "JOB-8794", taskId: "TSK-1033", endpoint: "POST /api/runner/jobs/{id}/fail", status: "blocked", attempt: 2, nextPollAt: "manual" }
];

export const members: Member[] = [
  { id: "MBR-210", name: "Avery Chen", role: "admin", plan: "Team", lastSeen: "2 min ago" },
  { id: "MBR-184", name: "Noah Kim", role: "member", plan: "Team", lastSeen: "12 min ago" },
  { id: "MBR-122", name: "Mira Patel", role: "user", plan: "Starter", lastSeen: "1 hr ago" }
];

export const orders: Order[] = [
  { id: "ORD-7331", member: "Avery Chen", amount: "$240.00", state: "paid", createdAt: "Today" },
  { id: "ORD-7328", member: "Noah Kim", amount: "$89.00", state: "pending", createdAt: "Today" },
  { id: "ORD-7319", member: "Mira Patel", amount: "$19.00", state: "refunded", createdAt: "Yesterday" }
];

export const auditEvents: AuditEvent[] = [
  { id: "AUD-7009", actor: "admin", action: "changed role", target: "MBR-184", at: "09:43" },
  { id: "AUD-7008", actor: "runner-east-1", action: "claimed task", target: "TSK-1042", at: "09:42" },
  { id: "AUD-7002", actor: "api", action: "opened sqlite transaction", target: "main.db", at: "09:40" },
  { id: "AUD-6998", actor: "user", action: "created order", target: "ORD-7331", at: "09:16" }
];

export const health: HealthSnapshot = {
  api: "healthy",
  database: "healthy",
  runner: "degraded",
  latencyMs: 42,
  sqlitePath: "data/app.sqlite",
  queueDepth: 7,
  failedJobs: 1
};

export const hermesConfig: HermesConfig = {
  enabled: true,
  model: "anthropic/claude-sonnet-4.6",
  provider: "anthropic",
  base_url: "",
  api_key_configured: false,
  task_root: "/runner/workspaces",
  hermes_home: "/runner/.hermes",
  max_iterations: 20,
  default_toolsets: ["safe"],
  allowed_toolsets: ["safe", "web", "search", "vision", "image_gen", "mcp-sqlite-service"],
  memory_mode: "tenant",
  timeout_seconds: 300,
  updated_at: null
};

export const chatMessages = [
  { from: "user", text: "Can the runner retry the invoice snapshot task?" },
  { from: "assistant", text: "Yes. The current queue policy allows two retries before admin review." },
  { from: "user", text: "Show me the task that is blocked." }
];
