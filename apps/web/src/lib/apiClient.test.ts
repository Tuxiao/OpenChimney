import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "./apiClient";

describe("ApiClient", () => {
  it("uses local mock data when no base URL is provided", async () => {
    const client = new ApiClient({ baseUrl: "" });
    const result = await client.tasks();

    expect(result.length).toBeGreaterThan(0);
    expect(result[0]).toHaveProperty("id");
  });

  it("requests FastAPI-compatible routes when a base URL is configured", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ api: "healthy" }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher });

    await client.health();

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/health", { headers: { Accept: "application/json" } });
  });

  it("posts phone auth requests to the FastAPI auth endpoints", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ phone: "+15551234567", dev_code: "123456", expires_at: "2026-05-30T00:00:00Z" }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher });

    await client.requestPhoneCode("+1 (555) 123-4567");

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/auth/phone/request-code", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ phone: "+1 (555) 123-4567" })
    });
  });

  it("posts email password login to the FastAPI auth endpoint", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ token: { access_token: "token" } }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher });

    await client.loginWithEmail("superadmin@example.com", "superadmin1234");

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ email: "superadmin@example.com", password: "superadmin1234" })
    });
  });

  it("sets phone account password with bearer auth", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ has_password: true, requires_password_setup: false }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher, token: "phone-token" });

    await client.setPassword("password123");

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/auth/set-password", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: "Bearer phone-token" },
      body: JSON.stringify({ password: "password123" })
    });
  });

  it("surfaces FastAPI error detail messages", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "Password is not set for this phone. Sign in with SMS first." }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        })
    ) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher });

    await expect(client.loginWithPhonePassword("+15551234567", "password123")).rejects.toThrow("Password is not set for this phone. Sign in with SMS first.");
  });

  it("saves Hermes settings through the admin endpoint", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ enabled: true, model: "openai/gpt-4.1" }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher, token: "admin-token" });
    const payload = {
      enabled: true,
      model: "openai/gpt-4.1",
      provider: "openai",
      base_url: "https://models.example.com/v1",
      api_key: "secret",
      task_root: "/runner/jobs",
      hermes_home: "/runner/hermes",
      max_iterations: 10,
      default_toolsets: ["safe"],
      allowed_toolsets: ["safe"],
      memory_mode: "project" as const,
      timeout_seconds: 120
    };

    await client.saveHermesConfig(payload);

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/admin/hermes-config", {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: "Bearer admin-token" },
      body: JSON.stringify(payload)
    });
  });

  it("saves Hermes config through the admin endpoint", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ model: "openai/gpt-4.1" }), { status: 200 })) as unknown as typeof fetch;
    const client = new ApiClient({ baseUrl: "http://localhost:8000", fetcher, token: "token-a" });

    await client.saveHermesConfig({
      enabled: true,
      model: "openai/gpt-4.1",
      provider: "openai",
      base_url: "https://llm.example.test/v1",
      api_key: "secret-model-key",
      task_root: "/runner/tasks",
      hermes_home: "/runner/hermes-home",
      max_iterations: 12,
      default_toolsets: ["safe"],
      allowed_toolsets: ["safe", "web"],
      memory_mode: "project",
      timeout_seconds: 180
    });

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/api/admin/hermes-config", {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json", Authorization: "Bearer token-a" },
      body: JSON.stringify({
        enabled: true,
        model: "openai/gpt-4.1",
        provider: "openai",
        base_url: "https://llm.example.test/v1",
        api_key: "secret-model-key",
        task_root: "/runner/tasks",
        hermes_home: "/runner/hermes-home",
        max_iterations: 12,
        default_toolsets: ["safe"],
        allowed_toolsets: ["safe", "web"],
        memory_mode: "project",
        timeout_seconds: 180
      })
    });
  });
});
