# Frontend

The web app lives in `apps/web` and is an isolated React + Vite + TypeScript frontend for OpenChimney.

## Scope

- Formal public product shell with Landing, Pricing, phone login, first-login password setup, and a product footer.
- Landing page with hero, module overview, backend-runner REST polling explanation, and SQLite operation examples.
- Pricing page with Starter, Pro, and Team plans wired to the login flow.
- Phone login supports both phone + SMS and phone + password. In local/demo mode the SMS code is shown on the page for copy/paste.
- User console with sidebar navigation, task table, filters, selected task detail panel, compact chat, user center, and account pages.
- Super admin console with service health, SQLite status, runner polling card, queue overview, failures, members/orders previews, audit stream, and admin nav pages.
- Local mock data by default, with `VITE_API_BASE_URL` enabling FastAPI-backed requests through `src/lib/apiClient.ts`.

## Commands

```bash
cd apps/web
npm install
npm run dev
npm run build
npm run test
```

The API client currently targets these route shapes:

- `GET /api/health`
- `GET /api/tasks`
- `GET /api/admin/runner-jobs`
- `GET /api/members`
- `GET /api/orders`
- `GET /api/admin/audit-logs`
- `POST /api/auth/phone/request-code`
- `POST /api/auth/phone/verify-code`
- `POST /api/auth/phone/login`
- `POST /api/auth/set-password`

When `VITE_API_BASE_URL` is empty, the frontend uses local mock responses. When it points at the FastAPI service, the phone SMS flow auto-registers unknown phone numbers and returns `requires_password_setup=true`, which sends the user to the password setup screen before entering the console.
