import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bell,
  Bot,
  Check,
  CheckCircle2,
  CircleUserRound,
  Database,
  ExternalLink,
  FileText,
  KeyRound,
  LayoutDashboard,
  ListFilter,
  LockKeyhole,
  LogOut,
  MessageSquareText,
  PackageCheck,
  Phone,
  RefreshCw,
  Rows3,
  Search,
  Server,
  Settings,
  TerminalSquare,
  UserRoundCog,
  UsersRound
} from "lucide-react";
import { auditEvents, chatMessages, health, members, orders, runnerJobs, tasks } from "./data/mockData";
import { apiClient, ApiClient } from "./lib/apiClient";
import type {
  AuditEvent,
  AuthResponse,
  HermesConfig,
  HermesConfigInput,
  Member,
  Order,
  RunnerJob,
  ServiceState,
  Task,
  TaskStatus
} from "./types/domain";

type Route = "landing" | "pricing" | "login" | "set-password" | "user" | "admin";
type AuthState = { token: string; user: AuthResponse["user"] } | null;
type FooterLink = { label: string; route: Route } | { label: string; href: string };
type UserPage = "tasks" | "chat" | "user-center" | "account";
type AdminPage = "dashboard" | "members" | "orders" | "audit" | "settings";

const taskStatuses: Array<"all" | TaskStatus> = ["all", "queued", "running", "blocked", "done", "failed"];

export function App() {
  const [route, setRoute] = useState<Route>("landing");
  const [auth, setAuth] = useState<AuthState>(null);
  const [userPage, setUserPage] = useState<UserPage>("tasks");
  const [adminPage, setAdminPage] = useState<AdminPage>("dashboard");
  const authedApi = useMemo(() => new ApiClient({ token: auth?.token }), [auth?.token]);

  const handleAuth = (response: AuthResponse) => {
    setAuth({ token: response.token.access_token, user: response.user });
    const isAdmin = response.user.roles.some((role) => role.name === "admin");
    setRoute(response.requires_password_setup ? "set-password" : isAdmin ? "admin" : "user");
  };

  const handlePasswordSet = (user: AuthResponse["user"]) => {
    setAuth((current) => (current ? { ...current, user } : current));
    setRoute("user");
  };

  const signOut = () => {
    setAuth(null);
    setRoute("landing");
  };

  const publicRoute = route === "landing" || route === "pricing" || route === "login" || route === "set-password";

  return (
    <div className="min-h-screen bg-mist text-ink">
      {publicRoute ? (
        <>
          <ProductHeader route={route} onNavigate={setRoute} authed={Boolean(auth)} />
          {route === "landing" && <LandingPage onGetStarted={() => setRoute("login")} onPricing={() => setRoute("pricing")} />}
          {route === "pricing" && <PricingPage onGetStarted={() => setRoute("login")} />}
          {route === "login" && <LoginPage onAuthenticated={handleAuth} />}
          {route === "set-password" && auth && <SetPasswordPage api={authedApi} token={auth.token} onComplete={handlePasswordSet} />}
          <ProductFooter onNavigate={setRoute} />
        </>
      ) : (
        <>
          <AuthenticatedHeader
            route={route}
            userLabel={auth?.user.phone ?? auth?.user.email ?? "Local user"}
            onNavigate={setRoute}
            onSignOut={signOut}
          />
          {route === "user" && <UserConsole page={userPage} onPageChange={setUserPage} />}
          {route === "admin" && <AdminConsole api={authedApi} page={adminPage} onPageChange={setAdminPage} />}
        </>
      )}
    </div>
  );
}

function ProductHeader({ route, onNavigate, authed }: { route: Route; onNavigate: (route: Route) => void; authed: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <button className="flex items-center gap-3 text-left" onClick={() => onNavigate("landing")}>
          <span className="grid size-8 place-items-center border border-ink bg-ink text-paper">
            <Database size={16} />
          </span>
          <span className="text-base font-semibold">SQLite Service Kit</span>
        </button>
        <nav className="hidden items-center gap-7 text-sm md:flex">
          <button className={route === "landing" ? "font-semibold text-ink" : "text-muted hover:text-ink"} onClick={() => onNavigate("landing")}>Landing</button>
          <button className={route === "pricing" ? "font-semibold text-ink" : "text-muted hover:text-ink"} onClick={() => onNavigate("pricing")}>Pricing</button>
          <a className="inline-flex items-center gap-1 text-muted hover:text-ink" href="#docs">Docs <ExternalLink size={13} /></a>
        </nav>
        <div className="flex items-center gap-2">
          {authed && (
            <button className="hidden h-10 border border-line px-3 text-sm font-medium text-ink hover:border-ink sm:inline-flex sm:items-center" onClick={() => onNavigate("user")}>
              Console
            </button>
          )}
          <button className="h-10 border border-line px-3 text-sm font-medium text-ink hover:border-ink" onClick={() => onNavigate("login")}>
            Sign in
          </button>
          <button className="btn-primary h-10" onClick={() => onNavigate("login")}>
            Get started
          </button>
        </div>
      </div>
    </header>
  );
}

function AuthenticatedHeader({
  route,
  userLabel,
  onNavigate,
  onSignOut
}: {
  route: Route;
  userLabel: string;
  onNavigate: (route: Route) => void;
  onSignOut: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <button className="flex items-center gap-2 text-left" onClick={() => onNavigate("user")}>
          <span className="grid size-8 place-items-center border border-ink bg-ink text-paper">
            <Database size={16} />
          </span>
          <span>
            <span className="block text-sm font-semibold leading-4">SQLite Service Kit</span>
            <span className="block text-[11px] leading-4 text-muted">Product console</span>
          </span>
        </button>
        <nav className="flex items-center gap-1 text-sm">
          <button className={`h-9 border px-3 ${route === "user" ? "border-ink bg-paper font-semibold" : "border-transparent text-muted hover:text-ink"}`} onClick={() => onNavigate("user")}>
            User console
          </button>
          <button className={`h-9 border px-3 ${route === "admin" ? "border-ink bg-paper font-semibold" : "border-transparent text-muted hover:text-ink"}`} onClick={() => onNavigate("admin")}>
            Admin
          </button>
        </nav>
        <div className="hidden items-center gap-2 text-sm sm:flex">
          <span className="max-w-[180px] truncate text-muted">{userLabel}</span>
          <button className="inline-flex h-9 items-center gap-2 border border-line px-3 font-medium hover:border-ink" onClick={onSignOut}>
            <LogOut size={15} />
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}

function LandingPage({ onGetStarted, onPricing }: { onGetStarted: () => void; onPricing: () => void }) {
  return (
    <main>
      <section className="border-b border-line bg-paper">
        <div className="mx-auto grid min-h-[520px] max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_520px] lg:items-center">
          <div className="max-w-2xl">
            <h1 className="max-w-xl text-4xl font-semibold leading-tight tracking-normal text-ink sm:text-5xl">
              SQLite backend template with consoles and a REST polling runner.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-muted">
              A compact starter for local accounts, roles, orders, tasks, Hermes-backed agent jobs, SQLite operations, and a runner that pulls work through ordinary HTTP routes.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <button className="btn-primary" onClick={onGetStarted}>
                Get started
                <ArrowRight size={16} />
              </button>
              <button className="btn-secondary" onClick={onPricing}>
                View pricing
              </button>
            </div>
          </div>
          <div className="border border-line bg-field">
            <div className="flex items-center justify-between border-b border-line bg-paper px-4 py-3">
              <div>
                <p className="text-sm font-semibold">Runtime snapshot</p>
                <p className="text-xs text-muted">Local mock data, API-ready route names</p>
              </div>
              <StatusPill status={health.runner} label="runner watched" />
            </div>
            <div className="divide-y divide-line">
              <SnapshotRow icon={<Server size={16} />} label="FastAPI service" value={`${health.latencyMs} ms`} state={health.api} />
              <SnapshotRow icon={<Database size={16} />} label="SQLite database" value={health.sqlitePath} state={health.database} />
              <SnapshotRow icon={<RefreshCw size={16} />} label="REST polling queue" value={`${health.queueDepth} jobs`} state={health.runner} />
              <SnapshotRow icon={<AlertTriangle size={16} />} label="Failed runner jobs" value={`${health.failedJobs} needs review`} state={health.failedJobs ? "degraded" : "healthy"} />
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-line bg-mist">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
          <SectionTitle title="Modules" copy="The template surface is deliberately operational: accounts, task work, agent execution, runner handoff, and admin review." />
          <div className="mt-6 grid gap-0 border border-line bg-paper md:grid-cols-4">
            <ModuleCell icon={<CircleUserRound size={18} />} title="Local accounts" copy="User, member, and admin roles without external identity requirements." />
            <ModuleCell icon={<PackageCheck size={18} />} title="Orders" copy="SQLite-backed order rows with a preview path for admin review." />
            <ModuleCell icon={<Rows3 size={18} />} title="Tasks" copy="Queueable work items, selected detail, status filters, and runner events." />
            <ModuleCell icon={<MessageSquareText size={18} />} title="Agent chat" copy="Hermes-ready conversation surfaces with local fallback data." />
          </div>
        </div>
      </section>

      <section className="border-b border-line bg-paper">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <SectionTitle title="Backend-runner communication" copy="The runner is independent from the web process and uses REST pull queue semantics." />
            <div className="mt-6 space-y-3 text-sm text-muted">
              <p>1. Runner claims work through `POST /api/runner/jobs/claim`.</p>
              <p>2. Claimed jobs heartbeat and report completion through task-scoped REST routes.</p>
              <p>3. Admins see queue depth, failed attempts, and audit events without direct runner coupling.</p>
            </div>
          </div>
          <div className="min-w-0 border border-line">
            <CompactTable
              columns={["Job", "Task", "Endpoint", "Status", "Next poll"]}
              rows={runnerJobs.map((job) => [job.id, job.taskId, job.endpoint, <StatusPill key={job.id} status={job.status} />, job.nextPollAt])}
            />
          </div>
        </div>
      </section>

      <section className="bg-mist">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
          <SectionTitle title="SQLite operations" copy="Tables, transactions, and audit trail are first-class UI concepts, not hidden implementation details." />
          <div className="mt-6 grid border border-line bg-paper md:grid-cols-3">
            <OperationCell title="Transactional writes" copy="Task and order mutations are represented as single logical operations." />
            <OperationCell title="Local database path" copy="Admin sees the active SQLite file and health without shell access." />
            <OperationCell title="Audit stream" copy="Account, runner, and database events share a compact chronological stream." />
          </div>
        </div>
      </section>
    </main>
  );
}

function PricingPage({ onGetStarted }: { onGetStarted: () => void }) {
  const plans = [
    {
      name: "Starter",
      price: "$0",
      copy: "For hobby projects and local apps.",
      features: ["SQLite database", "User and admin consoles", "REST API", "Polling task runner"]
    },
    {
      name: "Pro",
      price: "$19",
      copy: "For solo developers and small teams.",
      featured: true,
      features: ["Everything in Starter", "Backup export tools", "Health monitoring", "Priority email support"]
    },
    {
      name: "Team",
      price: "$49",
      copy: "For production apps and team operations.",
      features: ["Everything in Pro", "Role management", "Audit logs", "Multiple deployments"]
    }
  ];

  return (
    <main className="border-b border-line bg-paper">
      <section className="mx-auto grid max-w-7xl gap-8 px-4 py-16 sm:px-6 lg:grid-cols-[0.7fr_1.3fr]">
        <div>
          <h1 className="max-w-sm text-4xl font-semibold leading-tight">Simple pricing. Everything included.</h1>
          <p className="mt-4 max-w-sm text-base leading-7 text-muted">
            One SQLite-first codebase with public pages, user console, admin console, API, and remote runner.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {plans.map((plan) => (
            <section key={plan.name} className={`border bg-paper p-5 ${plan.featured ? "border-accent" : "border-line"}`}>
              <div className="flex min-h-8 items-start justify-between gap-3">
                <h2 className="text-base font-semibold">{plan.name}</h2>
                {plan.featured && <span className="text-xs font-semibold text-accent">Most popular</span>}
              </div>
              <p className="mt-3 text-3xl font-semibold">{plan.price}<span className="text-sm font-normal text-muted"> / month</span></p>
              <p className="mt-3 min-h-12 text-sm leading-6 text-muted">{plan.copy}</p>
              <ul className="mt-5 space-y-3 text-sm">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-2">
                    <Check className="mt-0.5 text-accent" size={15} />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <button className={plan.featured ? "btn-primary mt-6 w-full justify-center" : "btn-secondary mt-6 w-full justify-center"} onClick={onGetStarted}>
                Get started
              </button>
            </section>
          ))}
        </div>
      </section>
    </main>
  );
}

function LoginPage({ onAuthenticated }: { onAuthenticated: (response: AuthResponse) => void }) {
  const [mode, setMode] = useState<"sms" | "phone-password" | "email-password">("sms");
  const [phone, setPhone] = useState("+1 (555) 123-4567");
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submitCodeRequest = async () => {
    setBusy(true);
    setError("");
    try {
      const response = await apiClient.requestPhoneCode(phone);
      setPhone(response.phone);
      setDevCode(response.dev_code);
      setCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send code");
    } finally {
      setBusy(false);
    }
  };

  const submitSmsLogin = async () => {
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await apiClient.verifyPhoneCode(phone, code));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to verify code");
    } finally {
      setBusy(false);
    }
  };

  const submitPasswordLogin = async () => {
    setBusy(true);
    setError("");
    try {
      onAuthenticated(
        mode === "email-password"
          ? await apiClient.loginWithEmail(email, password)
          : await apiClient.loginWithPhonePassword(phone, password)
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="border-b border-line bg-mist">
      <section className="mx-auto grid min-h-[620px] max-w-7xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_420px] lg:items-center">
        <div className="max-w-xl">
          <h1 className="text-4xl font-semibold leading-tight">Sign in with phone, then keep working.</h1>
          <p className="mt-4 text-base leading-7 text-muted">
            SMS login creates the account automatically on first use. New accounts go straight to password setup before entering the console.
          </p>
          <div className="mt-8 grid border border-line bg-paper md:grid-cols-3">
            <OperationCell title="1. Phone" copy="Enter a verified phone number." />
            <OperationCell title="2. SMS code" copy="Copy the development code into the form." />
            <OperationCell title="3. Password" copy="First login lands on password setup." />
          </div>
        </div>
        <section className="border border-line bg-paper">
          <div className="grid grid-cols-3 border-b border-line">
            <button className={`h-12 text-sm font-semibold ${mode === "sms" ? "border-b-2 border-accent text-accent" : "text-muted"}`} onClick={() => setMode("sms")}>
              Phone + SMS
            </button>
            <button className={`h-12 text-sm font-semibold ${mode === "phone-password" ? "border-b-2 border-accent text-accent" : "text-muted"}`} onClick={() => setMode("phone-password")}>
              Phone password
            </button>
            <button className={`h-12 text-sm font-semibold ${mode === "email-password" ? "border-b-2 border-accent text-accent" : "text-muted"}`} onClick={() => setMode("email-password")}>
              Admin email
            </button>
          </div>
          <div className="space-y-4 p-5">
            {mode === "email-password" ? (
              <label className="block">
                <span className="mb-2 block text-sm font-medium">Email</span>
                <div className="flex h-11 items-center border border-line bg-field px-3 focus-within:border-accent">
                  <UserRoundCog size={16} className="mr-2 text-muted" />
                  <input className="min-w-0 flex-1 bg-transparent text-sm outline-none" value={email} onChange={(event) => setEmail(event.target.value)} />
                </div>
              </label>
            ) : (
              <label className="block">
                <span className="mb-2 block text-sm font-medium">Phone number</span>
                <div className="flex h-11 items-center border border-line bg-field px-3 focus-within:border-accent">
                  <Phone size={16} className="mr-2 text-muted" />
                  <input className="min-w-0 flex-1 bg-transparent text-sm outline-none" value={phone} onChange={(event) => setPhone(event.target.value)} />
                </div>
              </label>
            )}

            {mode === "phone-password" || mode === "email-password" ? (
              <>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Password</span>
                  <div className="flex h-11 items-center border border-line bg-field px-3 focus-within:border-accent">
                    <LockKeyhole size={16} className="mr-2 text-muted" />
                    <input className="min-w-0 flex-1 bg-transparent text-sm outline-none" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
                  </div>
                </label>
                <button className="btn-primary w-full justify-center" disabled={busy} onClick={submitPasswordLogin}>
                  Sign in
                </button>
              </>
            ) : (
              <>
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">SMS code</span>
                    <input className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" value={code} onChange={(event) => setCode(event.target.value)} placeholder="6-digit code" />
                  </label>
                  <button className="mt-7 h-11 border border-line px-3 text-sm font-semibold hover:border-ink" disabled={busy} onClick={submitCodeRequest}>
                    Send
                  </button>
                </div>
                {devCode && (
                  <div className="border border-accent bg-accentSoft p-3 text-sm">
                    <p className="font-semibold text-accent">Development SMS code</p>
                    <button className="mt-1 font-mono text-2xl font-semibold text-ink" onClick={() => setCode(devCode)}>
                      {devCode}
                    </button>
                  </div>
                )}
                <button className="btn-primary w-full justify-center" disabled={busy || !code} onClick={submitSmsLogin}>
                  Continue
                </button>
              </>
            )}
            {error && <p className="border border-line bg-field p-3 text-sm text-ink">{error}</p>}
          </div>
        </section>
      </section>
    </main>
  );
}

function SetPasswordPage({ api, token, onComplete }: { api: ApiClient; token: string; onComplete: (user: AuthResponse["user"]) => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    try {
      onComplete(await api.setPassword(password, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to set password");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="border-b border-line bg-mist">
      <section className="mx-auto grid min-h-[620px] max-w-7xl place-items-center px-4 py-14 sm:px-6">
        <div className="w-full max-w-md border border-line bg-paper p-5">
          <div className="mx-auto grid size-14 place-items-center border border-accent bg-accentSoft text-accent">
            <LockKeyhole size={24} />
          </div>
          <h1 className="mt-5 text-center text-2xl font-semibold">Set your password</h1>
          <p className="mt-2 text-center text-sm leading-6 text-muted">Create a password for future phone + password sign in.</p>
          <div className="mt-6 space-y-4">
            <input className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" type="password" placeholder="Password" value={password} onChange={(event) => setPassword(event.target.value)} />
            <input className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" type="password" placeholder="Confirm password" value={confirm} onChange={(event) => setConfirm(event.target.value)} />
            <button className="btn-primary w-full justify-center" disabled={busy || password.length < 8 || confirm.length < 8} onClick={submit}>
              Create account
            </button>
            {error && <p className="border border-line bg-field p-3 text-sm">{error}</p>}
          </div>
        </div>
      </section>
    </main>
  );
}

function ProductFooter({ onNavigate }: { onNavigate: (route: Route) => void }) {
  const productLinks: FooterLink[] = [
    { label: "Overview", route: "landing" },
    { label: "Pricing", route: "pricing" },
    { label: "Phone login", route: "login" }
  ];
  const resourceLinks: FooterLink[] = [
    { label: "Architecture", href: "#docs" },
    { label: "API endpoints", href: "#docs" },
    { label: "Runner protocol", href: "#docs" }
  ];
  const deployLinks: FooterLink[] = [
    { label: "FastAPI service", href: "#docs" },
    { label: "React web app", href: "#docs" },
    { label: "Remote runner", href: "#docs" }
  ];
  const companyLinks: FooterLink[] = [
    { label: "Security", href: "#docs" },
    { label: "Terms", href: "#docs" },
    { label: "Contact", href: "mailto:team@example.com" }
  ];

  return (
    <footer id="docs" className="border-t border-line bg-ink text-paper">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid gap-6 border-b border-white/10 py-8 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <h2 className="text-xl font-semibold">Build the product surface and the worker boundary together.</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#c7ced8]">
              Start with public pages, phone auth, user operations, admin review, and a separately deployed task runner that talks to the API over REST.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="inline-flex h-10 items-center gap-2 border border-paper bg-paper px-4 text-sm font-semibold text-ink hover:bg-[#edf2f7]" onClick={() => onNavigate("login")}>
              Get started
              <ArrowRight size={15} />
            </button>
            <button className="inline-flex h-10 items-center gap-2 border border-white/25 px-4 text-sm font-semibold text-paper hover:border-paper" onClick={() => onNavigate("pricing")}>
              View pricing
            </button>
          </div>
        </div>

        <div className="grid gap-8 py-10 md:grid-cols-[1.35fr_0.8fr_0.8fr_0.8fr_0.8fr]">
          <div>
            <div className="flex items-center gap-3">
              <span className="grid size-9 place-items-center border border-paper bg-paper text-ink">
                <Database size={17} />
              </span>
              <span className="text-base font-semibold">SQLite Service Kit</span>
            </div>
            <p className="mt-4 max-w-sm text-sm leading-6 text-[#c7ced8]">
              SQLite-first starter for public acquisition, user console workflows, super admin operations, REST API, and remote AI task runners.
            </p>
            <div className="mt-5 grid max-w-sm gap-2 text-xs text-[#c7ced8] sm:grid-cols-2">
              <span className="border border-white/10 px-3 py-2">SQLite WAL-ready</span>
              <span className="border border-white/10 px-3 py-2">REST runner polling</span>
              <span className="border border-white/10 px-3 py-2">Phone auth flow</span>
              <span className="border border-white/10 px-3 py-2">Admin audit views</span>
            </div>
          </div>
          <FooterColumn title="Product" links={productLinks} onNavigate={onNavigate} />
          <FooterColumn title="Resources" links={resourceLinks} onNavigate={onNavigate} />
          <FooterColumn title="Deploy" links={deployLinks} onNavigate={onNavigate} />
          <FooterColumn title="Company" links={companyLinks} onNavigate={onNavigate} />
        </div>

        <div className="flex flex-col gap-3 border-t border-white/10 py-5 text-xs text-[#aeb8c5] sm:flex-row sm:items-center sm:justify-between">
          <p>(c) 2026 SQLite Service Kit. Template code for local-first products.</p>
          <div className="flex flex-wrap gap-4">
            <a className="hover:text-paper" href="#docs">Privacy</a>
            <a className="hover:text-paper" href="#docs">Terms</a>
            <a className="hover:text-paper" href="#docs">Security</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({ title, links, onNavigate }: { title: string; links: FooterLink[]; onNavigate: (route: Route) => void }) {
  return (
    <div>
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-4 space-y-3 text-sm text-[#c7ced8]">
        {links.map((link) =>
          "route" in link ? (
            <button key={link.label} className="block text-left hover:text-paper" onClick={() => onNavigate(link.route)}>
              {link.label}
            </button>
          ) : (
            <a key={link.label} className="block hover:text-paper" href={link.href}>
              {link.label}
            </a>
          )
        )}
      </div>
    </div>
  );
}

function UserConsole({ page, onPageChange }: { page: UserPage; onPageChange: (page: UserPage) => void }) {
  const [statusFilter, setStatusFilter] = useState<"all" | TaskStatus>("all");
  const [query, setQuery] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState(tasks[0].id);
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0];

  const visibleTasks = useMemo(() => {
    return tasks.filter((task) => {
      const matchesStatus = statusFilter === "all" || task.status === statusFilter;
      const matchesQuery = [task.id, task.title, task.owner, task.runner].join(" ").toLowerCase().includes(query.toLowerCase());
      return matchesStatus && matchesQuery;
    });
  }, [query, statusFilter]);

  return (
    <ConsoleLayout
      title="User console"
      navItems={[
        { id: "tasks", label: "Tasks", icon: <Rows3 size={16} /> },
        { id: "chat", label: "AI chat", icon: <Bot size={16} /> },
        { id: "user-center", label: "User center", icon: <UsersRound size={16} /> },
        { id: "account", label: "Account", icon: <KeyRound size={16} /> }
      ]}
      active={page}
      onChange={(value) => onPageChange(value as UserPage)}
    >
      {page === "tasks" && (
        <div className="grid min-h-[calc(100vh-7rem)] gap-4 lg:grid-cols-[1fr_360px]">
          <section className="border border-line bg-paper">
            <div className="flex flex-col gap-3 border-b border-line px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold">Task management</h2>
                <p className="text-sm text-muted">Filter, select, and review runner-owned work.</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 text-muted" size={15} />
                  <input className="h-10 w-56 border border-line bg-field pl-9 pr-3 text-sm outline-none focus:border-accent" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks" />
                </div>
                <ListFilter size={16} className="text-muted" />
                <select className="h-10 border border-line bg-field px-3 text-sm outline-none focus:border-accent" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | TaskStatus)}>
                  {taskStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line bg-field text-xs uppercase text-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Task</th>
                    <th className="px-4 py-3 font-medium">Owner</th>
                    <th className="px-4 py-3 font-medium">Priority</th>
                    <th className="px-4 py-3 font-medium">Runner</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {visibleTasks.map((task) => (
                    <tr key={task.id} className={`cursor-pointer transition hover:bg-field ${selectedTask.id === task.id ? "bg-accentSoft" : "bg-paper"}`} onClick={() => setSelectedTaskId(task.id)}>
                      <td className="px-4 py-3">
                        <span className="block font-medium">{task.title}</span>
                        <span className="text-xs text-muted">{task.id} · updated {task.updatedAt}</span>
                      </td>
                      <td className="px-4 py-3 text-muted">{task.owner}</td>
                      <td className="px-4 py-3 capitalize">{task.priority}</td>
                      <td className="px-4 py-3 text-muted">{task.runner}</td>
                      <td className="px-4 py-3">
                        <StatusPill status={task.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <TaskDetail task={selectedTask} />
        </div>
      )}
      {page === "chat" && <ChatPanel />}
      {page === "user-center" && <UserCenter />}
      {page === "account" && <AccountPanel />}
    </ConsoleLayout>
  );
}

function AdminConsole({ api, page, onPageChange }: { api: ApiClient; page: AdminPage; onPageChange: (page: AdminPage) => void }) {
  return (
    <ConsoleLayout
      title="Super admin"
      navItems={[
        { id: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
        { id: "members", label: "Members", icon: <UsersRound size={16} /> },
        { id: "orders", label: "Orders", icon: <FileText size={16} /> },
        { id: "audit", label: "Audit", icon: <Activity size={16} /> },
        { id: "settings", label: "Settings", icon: <Settings size={16} /> }
      ]}
      active={page}
      onChange={(value) => onPageChange(value as AdminPage)}
    >
      {page === "dashboard" && <AdminDashboard />}
      {page === "members" && <PreviewList title="Members" rows={members} renderRow={(member) => <MemberRow member={member} />} />}
      {page === "orders" && <PreviewList title="Orders" rows={orders} renderRow={(order) => <OrderRow order={order} />} />}
      {page === "audit" && <AuditStream events={auditEvents} />}
      {page === "settings" && <SettingsPanel api={api} />}
    </ConsoleLayout>
  );
}

function AdminDashboard() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-4">
        <HealthBox icon={<Server size={18} />} label="API service" value={`${health.latencyMs} ms`} state={health.api} />
        <HealthBox icon={<Database size={18} />} label="SQLite status" value={health.sqlitePath} state={health.database} />
        <HealthBox icon={<RefreshCw size={18} />} label="Runner polling" value={`${health.queueDepth} queued`} state={health.runner} />
        <HealthBox icon={<AlertTriangle size={18} />} label="Failures" value={`${health.failedJobs} open`} state={health.failedJobs ? "degraded" : "healthy"} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="border border-line bg-paper">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Runner queue overview</h2>
            <p className="text-sm text-muted">Independent runner pulls work, heartbeats status, and writes completion through API routes.</p>
          </div>
          <CompactTable
            columns={["Job", "Task", "Endpoint", "Attempt", "Status"]}
            rows={runnerJobs.map((job) => [job.id, job.taskId, job.endpoint, job.attempt, <StatusPill key={job.id} status={job.status} />])}
          />
        </section>
        <section className="border border-line bg-paper">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-base font-semibold">Audit stream</h2>
            <p className="text-sm text-muted">Recent account, runner, and SQLite events.</p>
          </div>
          <AuditStream events={auditEvents} compact />
        </section>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <PreviewList title="Members preview" rows={members} renderRow={(member) => <MemberRow member={member} />} />
        <PreviewList title="Orders preview" rows={orders} renderRow={(order) => <OrderRow order={order} />} />
      </div>
    </div>
  );
}

function ConsoleLayout<T extends string>({
  title,
  navItems,
  active,
  onChange,
  children
}: {
  title: string;
  navItems: Array<{ id: T; label: string; icon: ReactNode }>;
  active: T;
  onChange: (value: T) => void;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto grid max-w-7xl gap-0 px-4 py-4 sm:px-6 lg:grid-cols-[220px_1fr]">
      <aside className="border border-line bg-paper lg:min-h-[calc(100vh-5.5rem)]">
        <div className="border-b border-line px-4 py-4">
          <h1 className="text-base font-semibold">{title}</h1>
          <p className="text-xs text-muted">Local roles and mock API state</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto p-2 lg:block lg:space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`flex h-10 shrink-0 items-center gap-2 px-3 text-sm transition lg:w-full ${
                active === item.id ? "bg-accentSoft font-medium text-accent" : "text-muted hover:bg-field hover:text-ink"
              }`}
              onClick={() => onChange(item.id)}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <main className="pt-4 lg:pl-4 lg:pt-0">{children}</main>
    </div>
  );
}

function TaskDetail({ task }: { task: Task }) {
  return (
    <aside className="border border-line bg-paper">
      <div className="border-b border-line px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{task.id}</h2>
          <StatusPill status={task.status} />
        </div>
        <p className="mt-1 text-sm text-muted">{task.title}</p>
      </div>
      <div className="space-y-5 p-4">
        <DetailBlock label="Detail" value={task.details} />
        <TaskChat />
        <div>
          <p className="mb-2 text-xs font-semibold uppercase text-muted">Runner events</p>
          <ol className="space-y-2">
            {task.events.map((event) => (
              <li key={event} className="flex gap-2 text-sm">
                <CheckCircle2 className="mt-0.5 text-accent" size={15} />
                <span>{event}</span>
              </li>
            ))}
          </ol>
        </div>
        <div className="grid grid-cols-2 border border-line">
          <MetricCell label="Owner" value={task.owner} />
          <MetricCell label="Priority" value={task.priority} />
          <MetricCell label="Runner" value={task.runner} />
          <MetricCell label="Updated" value={task.updatedAt} />
        </div>
      </div>
    </aside>
  );
}

function TaskChat() {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase text-muted">AI chat</p>
      <div className="space-y-2">
        {chatMessages.slice(0, 3).map((message, index) => (
          <div
            key={`${message.from}-${index}`}
            className={`border border-line px-3 py-2 text-sm ${
              message.from === "user" ? "bg-accentSoft" : "bg-field"
            }`}
          >
            <span className="mb-1 block text-[11px] font-semibold uppercase text-muted">
              {message.from}
            </span>
            <span className="leading-5">{message.text}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 flex border border-line bg-field">
        <input
          className="h-10 min-w-0 flex-1 bg-transparent px-3 text-sm outline-none"
          placeholder="Message this task"
        />
        <button className="h-10 border-l border-line px-3 text-sm font-medium text-accent">
          Send
        </button>
      </div>
    </div>
  );
}

function ChatPanel() {
  return (
    <section className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="border border-line bg-paper">
        <div className="border-b border-line px-4 py-4">
          <h2 className="text-lg font-semibold">Compact AI chat</h2>
          <p className="text-sm text-muted">Hermes agent conversation with local fallback state.</p>
        </div>
        <div className="space-y-3 p-4">
          {chatMessages.map((message, index) => (
            <div key={`${message.from}-${index}`} className={`max-w-[80%] border border-line px-3 py-2 text-sm ${message.from === "user" ? "ml-auto bg-accentSoft" : "bg-field"}`}>
              <span className="mb-1 block text-xs font-medium uppercase text-muted">{message.from}</span>
              {message.text}
            </div>
          ))}
          <div className="flex border border-line bg-field">
            <input className="h-11 flex-1 bg-transparent px-3 text-sm outline-none" placeholder="Ask about a task or order" />
            <button className="h-11 border-l border-line px-4 text-sm font-medium text-accent">Send</button>
          </div>
        </div>
      </div>
      <TaskDetail task={tasks[2]} />
    </section>
  );
}

function UserCenter() {
  return (
    <section className="border border-line bg-paper">
      <div className="border-b border-line px-4 py-4">
        <h2 className="text-lg font-semibold">User center</h2>
        <p className="text-sm text-muted">Local member profile and recent task ownership.</p>
      </div>
      <CompactTable columns={["Member", "Role", "Plan", "Last seen"]} rows={members.map((member) => [member.name, member.role, member.plan, member.lastSeen])} />
    </section>
  );
}

function AccountPanel() {
  return (
    <section className="border border-line bg-paper">
      <div className="border-b border-line px-4 py-4">
        <h2 className="text-lg font-semibold">Account</h2>
        <p className="text-sm text-muted">Local account settings and security state.</p>
      </div>
      <div className="grid divide-y divide-line">
        <SettingsRow icon={<CircleUserRound size={17} />} label="Display name" value="Avery Chen" />
        <SettingsRow icon={<KeyRound size={17} />} label="Password auth" value="Local credentials enabled" />
        <SettingsRow icon={<Bell size={17} />} label="Notifications" value="Task failures and runner downtime" />
      </div>
    </section>
  );
}

function PreviewList<T>({ title, rows, renderRow }: { title: string; rows: T[]; renderRow: (row: T) => ReactNode }) {
  return (
    <section className="border border-line bg-paper">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      <div className="divide-y divide-line">{rows.map((row, index) => <div key={index}>{renderRow(row)}</div>)}</div>
    </section>
  );
}

function MemberRow({ member }: { member: Member }) {
  return (
    <div className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 text-sm">
      <div>
        <p className="font-medium">{member.name}</p>
        <p className="text-xs text-muted">{member.id} · {member.plan}</p>
      </div>
      <StatusPill status="healthy" label={member.role} />
    </div>
  );
}

function OrderRow({ order }: { order: Order }) {
  return (
    <div className="grid grid-cols-[1fr_auto] gap-3 px-4 py-3 text-sm">
      <div>
        <p className="font-medium">{order.id}</p>
        <p className="text-xs text-muted">{order.member} · {order.createdAt}</p>
      </div>
      <div className="text-right">
        <p className="font-medium">{order.amount}</p>
        <p className="text-xs capitalize text-muted">{order.state}</p>
      </div>
    </div>
  );
}

function AuditStream({ events, compact = false }: { events: AuditEvent[]; compact?: boolean }) {
  return (
    <section className={compact ? "" : "border border-line bg-paper"}>
      {!compact && (
        <div className="border-b border-line px-4 py-4">
          <h2 className="text-lg font-semibold">Audit stream</h2>
          <p className="text-sm text-muted">Chronological operational events.</p>
        </div>
      )}
      <div className="divide-y divide-line">
        {events.map((event) => (
          <div key={event.id} className="grid grid-cols-[auto_1fr_auto] gap-3 px-4 py-3 text-sm">
            <TerminalSquare className="mt-0.5 text-accent" size={16} />
            <div>
              <p className="font-medium">{event.action}</p>
              <p className="text-xs text-muted">{event.actor} · {event.target}</p>
            </div>
            <span className="text-xs text-muted">{event.at}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SettingsPanel({ api }: { api: ApiClient }) {
  const [config, setConfig] = useState<HermesConfig | null>(null);
  const [form, setForm] = useState<HermesConfigInput | null>(null);
  const [defaultToolsets, setDefaultToolsets] = useState("");
  const [allowedToolsets, setAllowedToolsets] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [clearApiKey, setClearApiKey] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  useEffect(() => {
    let active = true;
    setBusy(true);
    setStatus("");
    api
      .hermesConfig()
      .then((nextConfig) => {
        if (!active) {
          return;
        }
        setConfig(nextConfig);
        setForm(toHermesForm(nextConfig));
        setDefaultToolsets(nextConfig.default_toolsets.join(", "));
        setAllowedToolsets(nextConfig.allowed_toolsets.join(", "));
      })
      .catch((err) => {
        if (active) {
          setStatus(err instanceof Error ? err.message : "Unable to load Hermes settings");
        }
      })
      .finally(() => {
        if (active) {
          setBusy(false);
        }
      });
    return () => {
      active = false;
    };
  }, [api]);

  const updateForm = (patch: Partial<HermesConfigInput>) => {
    setForm((current) => (current ? { ...current, ...patch } : current));
  };

  const save = async () => {
    if (!form) {
      return;
    }
    setBusy(true);
    setStatus("");
    try {
      const payload: HermesConfigInput = {
        ...form,
        provider: emptyToNull(form.provider),
        base_url: emptyToNull(form.base_url),
        api_key: apiKey.trim() || null,
        clear_api_key: clearApiKey,
        default_toolsets: parseToolsets(defaultToolsets),
        allowed_toolsets: parseToolsets(allowedToolsets)
      };
      const saved = await api.saveHermesConfig(payload);
      setConfig(saved);
      setForm(toHermesForm(saved));
      setDefaultToolsets(saved.default_toolsets.join(", "));
      setAllowedToolsets(saved.allowed_toolsets.join(", "));
      setApiKey("");
      setClearApiKey(false);
      setStatus("Hermes settings saved. Restart the runner to re-read this configuration.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Unable to save Hermes settings");
    } finally {
      setBusy(false);
    }
  };

  if (!form) {
    return (
      <section className="border border-line bg-paper">
        <div className="border-b border-line px-4 py-4">
          <h2 className="text-lg font-semibold">Admin settings</h2>
          <p className="text-sm text-muted">Loading Hermes runtime configuration.</p>
        </div>
        <div className="p-4 text-sm text-muted">{status || "Loading..."}</div>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      <section className="border border-line bg-paper">
        <div className="flex flex-col gap-3 border-b border-line px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Hermes agent runtime</h2>
            <p className="text-sm text-muted">Runner reads this database-backed configuration during startup.</p>
          </div>
          <StatusPill status={form.enabled ? "healthy" : "degraded"} label={form.enabled ? "enabled" : "disabled"} />
        </div>

        <div className="grid gap-4 p-4 xl:grid-cols-2">
          <label className="flex items-center gap-3 border border-line bg-field px-3 py-3 text-sm">
            <input checked={form.enabled} type="checkbox" onChange={(event) => updateForm({ enabled: event.target.checked })} />
            <span>
              <span className="block font-medium">Enable Hermes runtime</span>
              <span className="block text-xs text-muted">When off, runner falls back to the stub runtime.</span>
            </span>
          </label>

          <HermesTextField label="Model" value={form.model} onChange={(value) => updateForm({ model: value })} />
          <HermesTextField label="Provider" placeholder="anthropic, openrouter, openai" value={form.provider ?? ""} onChange={(value) => updateForm({ provider: value })} />
          <HermesTextField label="Model base URL" placeholder="https://api.example.com/v1" value={form.base_url ?? ""} onChange={(value) => updateForm({ base_url: value })} />

          <label className="block">
            <span className="mb-2 block text-sm font-medium">API key</span>
            <input
              className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent"
              placeholder={config?.api_key_configured ? "Configured; leave blank to keep" : "Paste key"}
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
            />
          </label>

          <label className="flex items-center gap-3 border border-line bg-field px-3 py-3 text-sm">
            <input checked={clearApiKey} type="checkbox" onChange={(event) => setClearApiKey(event.target.checked)} />
            <span>
              <span className="block font-medium">Clear saved API key</span>
              <span className="block text-xs text-muted">Use only when rotating or removing the model credential.</span>
            </span>
          </label>

          <HermesTextField label="Task root" value={form.task_root} onChange={(value) => updateForm({ task_root: value })} />
          <HermesTextField label="Hermes home" value={form.hermes_home} onChange={(value) => updateForm({ hermes_home: value })} />

          <label className="block">
            <span className="mb-2 block text-sm font-medium">Max iterations</span>
            <input className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" min={1} max={200} type="number" value={form.max_iterations} onChange={(event) => updateForm({ max_iterations: Number(event.target.value) })} />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium">Timeout seconds</span>
            <input className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" min={1} max={3600} type="number" value={form.timeout_seconds} onChange={(event) => updateForm({ timeout_seconds: Number(event.target.value) })} />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium">Memory mode</span>
            <select className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent" value={form.memory_mode} onChange={(event) => updateForm({ memory_mode: event.target.value as HermesConfigInput["memory_mode"] })}>
              <option value="tenant">tenant</option>
              <option value="project">project</option>
              <option value="off">off</option>
            </select>
          </label>

          <HermesTextField label="Default toolsets" value={defaultToolsets} onChange={setDefaultToolsets} />
          <HermesTextField className="xl:col-span-2" label="Allowed toolsets" value={allowedToolsets} onChange={setAllowedToolsets} />
        </div>

        <div className="flex flex-col gap-3 border-t border-line px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-muted">
            {status || `Last saved: ${config?.updated_at ? new Date(config.updated_at).toLocaleString() : "not recorded"}`}
          </p>
          <button className="btn-primary justify-center" disabled={busy} onClick={save}>
            <Check size={16} />
            Save Hermes settings
          </button>
        </div>
      </section>

      <section className="border border-line bg-paper">
        <div className="border-b border-line px-4 py-4">
          <h2 className="text-lg font-semibold">Admin settings</h2>
          <p className="text-sm text-muted">Operational preferences for local service management.</p>
        </div>
        <div className="grid divide-y divide-line">
          <SettingsRow icon={<Database size={17} />} label="SQLite path" value={health.sqlitePath} />
          <SettingsRow icon={<RefreshCw size={17} />} label="Runner polling interval" value="15 seconds" />
          <SettingsRow icon={<UserRoundCog size={17} />} label="Role policy" value="Local accounts and explicit admin grants" />
        </div>
      </section>
    </div>
  );
}

function HermesTextField({
  label,
  value,
  onChange,
  placeholder,
  className = ""
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-2 block text-sm font-medium">{label}</span>
      <input
        className="h-11 w-full border border-line bg-field px-3 text-sm outline-none focus:border-accent"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function toHermesForm(config: HermesConfig): HermesConfigInput {
  return {
    enabled: config.enabled,
    model: config.model,
    provider: config.provider,
    base_url: config.base_url,
    task_root: config.task_root,
    hermes_home: config.hermes_home,
    max_iterations: config.max_iterations,
    default_toolsets: config.default_toolsets,
    allowed_toolsets: config.allowed_toolsets,
    memory_mode: config.memory_mode,
    timeout_seconds: config.timeout_seconds
  };
}

function emptyToNull(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed || null;
}

function parseToolsets(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item, index, items) => items.indexOf(item) === index);
}

function SectionTitle({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold tracking-normal">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
    </div>
  );
}

function ModuleCell({ icon, title, copy }: { icon: ReactNode; title: string; copy: string }) {
  return (
    <div className="border-b border-line p-5 md:border-b-0 md:border-r last:md:border-r-0">
      <div className="mb-4 text-accent">{icon}</div>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
    </div>
  );
}

function OperationCell({ title, copy }: { title: string; copy: string }) {
  return (
    <div className="border-b border-line p-5 md:border-b-0 md:border-r last:md:border-r-0">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
    </div>
  );
}

function SnapshotRow({ icon, label, value, state }: { icon: ReactNode; label: string; value: string; state: ServiceState }) {
  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-4 text-sm">
      <span className="text-accent">{icon}</span>
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-xs text-muted">{value}</p>
      </div>
      <StatusPill status={state} />
    </div>
  );
}

function HealthBox({ icon, label, value, state }: { icon: ReactNode; label: string; value: string; state: ServiceState }) {
  return (
    <section className="border border-line bg-paper p-4">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-accent">{icon}</span>
        <StatusPill status={state} />
      </div>
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 truncate text-base font-semibold">{value}</p>
    </section>
  );
}

function StatusPill({ status, label }: { status: TaskStatus | ServiceState; label?: string }) {
  const tone = status === "healthy" || status === "done" ? "border-accent bg-accentSoft text-accent" : status === "degraded" || status === "blocked" || status === "failed" ? "border-line bg-field text-ink" : "border-line bg-paper text-muted";
  return <span className={`inline-flex h-6 items-center border px-2 text-xs font-medium capitalize ${tone}`}>{label ?? status}</span>;
}

function CompactTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <div className="min-w-0 max-w-full overflow-x-auto">
      <table className="min-w-[620px] w-full text-left text-sm">
        <thead className="border-b border-line bg-field text-xs uppercase text-muted">
          <tr>{columns.map((column) => <th key={column} className="px-4 py-3 font-medium">{column}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="bg-paper">
              {row.map((cell, cellIndex) => <td key={cellIndex} className="whitespace-nowrap px-4 py-3 text-muted first:font-medium first:text-ink">{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase text-muted">{label}</p>
      <p className="text-sm leading-6 text-ink">{value}</p>
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-r border-line p-3 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
      <p className="text-xs uppercase text-muted">{label}</p>
      <p className="mt-1 truncate text-sm font-medium capitalize">{value}</p>
    </div>
  );
}

function SettingsRow({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="grid grid-cols-[auto_1fr] gap-3 px-4 py-4 text-sm">
      <span className="text-accent">{icon}</span>
      <div>
        <p className="font-medium">{label}</p>
        <p className="text-muted">{value}</p>
      </div>
    </div>
  );
}
