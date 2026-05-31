export type TaskStatus = "open" | "queued" | "running" | "blocked" | "completed" | "done" | "failed";
export type TaskPriority = "low" | "normal" | "high";
export type ServiceState = "healthy" | "degraded" | "offline";

export interface Task {
  id: string;
  title: string;
  owner: string;
  status: TaskStatus;
  priority: TaskPriority;
  runner: string;
  updatedAt: string;
  details: string;
  events: string[];
}

export interface ApiTask {
  id: number;
  owner_user_id: number;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageAttachment {
  id: number;
  file_name: string;
  content_type?: string | null;
  url: string;
  size_bytes?: number | null;
  created_at: string;
}

export interface ConversationMessage {
  id: number;
  conversation_id: number;
  sender_user_id?: number | null;
  role: string;
  content: string;
  metadata_json: Record<string, unknown>;
  attachments: MessageAttachment[];
  created_at: string;
}

export interface Conversation {
  id: number;
  owner_user_id: number;
  task_id?: number | null;
  title: string;
  status: string;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string;
}

export interface TaskMessageResponse {
  message: ConversationMessage;
  runner_job_id: number;
}

export interface RunnerJob {
  id: string;
  taskId: string;
  endpoint: string;
  status: TaskStatus;
  attempt: number;
  nextPollAt: string;
}

export interface Member {
  id: string;
  name: string;
  role: "user" | "member" | "admin";
  plan: string;
  lastSeen: string;
}

export interface Order {
  id: string;
  member: string;
  amount: string;
  state: "paid" | "pending" | "refunded";
  createdAt: string;
}

export interface AuditEvent {
  id: string;
  actor: string;
  action: string;
  target: string;
  at: string;
}

export interface HealthSnapshot {
  api: ServiceState;
  database: ServiceState;
  runner: ServiceState;
  latencyMs: number;
  sqlitePath: string;
  queueDepth: number;
  failedJobs: number;
}

export interface HermesConfig {
  enabled: boolean;
  model: string;
  provider?: string | null;
  base_url?: string | null;
  api_key_configured: boolean;
  task_root: string;
  hermes_home: string;
  max_iterations: number;
  default_toolsets: string[];
  allowed_toolsets: string[];
  memory_mode: "tenant" | "project" | "off";
  timeout_seconds: number;
  updated_at?: string | null;
}

export interface HermesConfigInput {
  enabled: boolean;
  model: string;
  provider?: string | null;
  base_url?: string | null;
  api_key?: string | null;
  clear_api_key?: boolean;
  task_root: string;
  hermes_home: string;
  max_iterations: number;
  default_toolsets: string[];
  allowed_toolsets: string[];
  memory_mode: "tenant" | "project" | "off";
  timeout_seconds: number;
}

export interface AuthUser {
  id: number;
  email?: string | null;
  phone?: string | null;
  display_name?: string | null;
  is_active: boolean;
  has_password: boolean;
  requires_password_setup: boolean;
  roles: Array<{ id: number; name: string }>;
}

export interface AuthResponse {
  user: AuthUser;
  token: {
    access_token: string;
    token_type: string;
    expires_at: string;
  };
  is_new_user: boolean;
  requires_password_setup: boolean;
}

export interface PhoneCodeResponse {
  phone: string;
  expires_at: string;
  dev_code: string;
}
