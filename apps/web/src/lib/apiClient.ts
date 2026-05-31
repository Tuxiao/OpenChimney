import { auditEvents, health, hermesConfig, members, orders, runnerJobs, tasks } from "../data/mockData";
import type {
  ApiTask,
  AuditEvent,
  AuthResponse,
  Conversation,
  HealthSnapshot,
  HermesConfig,
  HermesConfigInput,
  Member,
  MessageAttachment,
  Order,
  PhoneCodeResponse,
  RunnerJob,
  Task,
  TaskMessageResponse,
  TaskPriority
} from "../types/domain";

type ApiOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
  token?: string;
};

const localDelay = 80;

const wait = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms));

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;
  private readonly token?: string;
  private readonly useMocks: boolean;

  constructor(options: ApiOptions = {}) {
    this.baseUrl = options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "";
    this.fetcher = options.fetcher ?? window.fetch.bind(window);
    this.token = options.token;
    this.useMocks = !this.baseUrl && (import.meta.env.DEV || import.meta.env.VITE_API_MOCKS === "1");
  }

  async health(): Promise<HealthSnapshot> {
    return this.get("/api/health", health);
  }

  async tasks(): Promise<Task[]> {
    return this.get("/api/tasks", tasks);
  }

  async apiTasks(): Promise<ApiTask[]> {
    return this.get("/api/tasks", []);
  }

  async createTask(payload: { title: string; description?: string; priority?: TaskPriority }): Promise<ApiTask> {
    return this.post("/api/tasks", {
      title: payload.title,
      description: payload.description ?? "",
      priority: payload.priority ?? "normal",
      status: "open"
    });
  }

  async sendTaskMessage(taskId: number, content: string): Promise<TaskMessageResponse> {
    return this.post(`/api/tasks/${taskId}/messages`, {
      role: "user",
      content,
      metadata_json: {}
    });
  }

  async conversations(): Promise<Conversation[]> {
    return this.get("/api/conversations", []);
  }

  async downloadAttachment(attachment: MessageAttachment): Promise<void> {
    const response = await this.fetcher(`${this.baseUrl}${attachment.url}`, {
      headers: {
        Accept: attachment.content_type || "application/octet-stream",
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {})
      }
    });
    if (!response.ok) {
      throw new Error(`Download failed with ${response.status}`);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = attachment.file_name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }

  async runnerQueue(): Promise<RunnerJob[]> {
    return this.get("/api/admin/runner-jobs", runnerJobs);
  }

  async members(): Promise<Member[]> {
    return this.get("/api/members", members);
  }

  async orders(): Promise<Order[]> {
    return this.get("/api/orders", orders);
  }

  async audit(): Promise<AuditEvent[]> {
    return this.get("/api/admin/audit-logs", auditEvents);
  }

  async hermesConfig(): Promise<HermesConfig> {
    return this.get("/api/admin/hermes-config", hermesConfig);
  }

  async saveHermesConfig(payload: HermesConfigInput): Promise<HermesConfig> {
    if (this.useMocks) {
      await wait(localDelay);
      return {
        ...hermesConfig,
        ...payload,
        api_key_configured: Boolean(payload.api_key) || hermesConfig.api_key_configured,
        updated_at: new Date().toISOString()
      };
    }
    return this.put("/api/admin/hermes-config", payload);
  }

  async requestPhoneCode(phone: string): Promise<PhoneCodeResponse> {
    if (this.useMocks) {
      await wait(localDelay);
      return {
        phone: normalizePhone(phone),
        expires_at: new Date(Date.now() + 5 * 60_000).toISOString(),
        dev_code: "123456"
      };
    }
    return this.post("/api/auth/phone/request-code", { phone });
  }

  async verifyPhoneCode(phone: string, code: string): Promise<AuthResponse> {
    if (this.useMocks) {
      await wait(localDelay);
      return mockAuth(normalizePhone(phone), true);
    }
    return this.post("/api/auth/phone/verify-code", { phone, code });
  }

  async loginWithPhonePassword(phone: string, password: string): Promise<AuthResponse> {
    if (this.useMocks) {
      await wait(localDelay);
      if (password.length < 8) {
        throw new Error("Password must contain at least 8 characters");
      }
      return mockAuth(normalizePhone(phone), false);
    }
    return this.post("/api/auth/phone/login", { phone, password });
  }

  async loginWithEmail(email: string, password: string): Promise<AuthResponse> {
    if (this.useMocks) {
      await wait(localDelay);
      if (password.length < 8) {
        throw new Error("Password must contain at least 8 characters");
      }
      return mockEmailAuth(email);
    }
    return this.post("/api/auth/login", { email, password });
  }

  async setPassword(password: string, token: string = this.token ?? ""): Promise<AuthResponse["user"]> {
    if (this.useMocks) {
      await wait(localDelay);
      return mockAuth("+15551234567", false).user;
    }
    return this.post("/api/auth/set-password", { password }, token);
  }

  private async get<T>(path: string, fallback: T): Promise<T> {
    if (this.useMocks) {
      await wait(localDelay);
      return structuredClone(fallback);
    }

    return readJson<T>(
      await this.fetcher(`${this.baseUrl}${path}`, {
        headers: {
          Accept: "application/json",
          ...(this.token ? { Authorization: `Bearer ${this.token}` } : {})
        }
      })
    );
  }

  private async post<T>(path: string, body: object, token: string = this.token ?? ""): Promise<T> {
    return readJson<T>(
      await this.fetcher(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(body)
      })
    );
  }

  private async put<T>(path: string, body: object, token: string = this.token ?? ""): Promise<T> {
    return readJson<T>(
      await this.fetcher(`${this.baseUrl}${path}`, {
        method: "PUT",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(body)
      })
    );
  }
}

export const apiClient = new ApiClient();

function normalizePhone(phone: string): string {
  const cleaned = phone.trim().replace(/[^\d+]/g, "");
  return cleaned.startsWith("00") ? `+${cleaned.slice(2)}` : cleaned;
}

function mockAuth(phone: string, requiresPasswordSetup: boolean): AuthResponse {
  return {
    user: {
      id: 1,
      email: null,
      phone,
      display_name: phone,
      is_active: true,
      has_password: !requiresPasswordSetup,
      requires_password_setup: requiresPasswordSetup,
      roles: [{ id: 1, name: "user" }]
    },
    token: {
      access_token: "local-demo-token",
      token_type: "bearer",
      expires_at: new Date(Date.now() + 30 * 24 * 60 * 60_000).toISOString()
    },
    is_new_user: requiresPasswordSetup,
    requires_password_setup: requiresPasswordSetup
  };
}

function mockEmailAuth(email: string): AuthResponse {
  return {
    user: {
      id: 1,
      email,
      phone: null,
      display_name: email,
      is_active: true,
      has_password: true,
      requires_password_setup: false,
      roles: [
        { id: 1, name: "user" },
        { id: 2, name: "super_admin" }
      ]
    },
    token: {
      access_token: "local-admin-token",
      token_type: "bearer",
      expires_at: new Date(Date.now() + 30 * 24 * 60 * 60_000).toISOString()
    },
    is_new_user: false,
    requires_password_setup: false
  };
}
