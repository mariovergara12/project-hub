# Project Hub frontend

React, TypeScript, and Vite. Supabase handles accounts; FastAPI handles project data.

## Run locally

From this directory:

```sh
npm ci
cp -n .env.example .env.local
```

Edit `.env.local`:

- `VITE_API_BASE_URL`: use `http://localhost:8000` for your local API.
- `VITE_SUPABASE_URL`: the shared Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY`: its public browser key.

Run `npm run dev` and open <http://localhost:5173>. Configure that exact origin
in the backend's `CORS_ORIGINS`. Never add database passwords, server keys, or demo
passwords to frontend configuration.

## Main screens

| Route | Purpose |
| --- | --- |
| `/` | Sign in or sign up. |
| `/forgot-password`, `/reset-password`, `/auth/callback` | Recovery and email confirmation. |
| `/main` | Find and filter projects. |
| `/profile` | Edit your profile, skills, and interests. New accounts get a setup guide. |
| `/my-projects`, `/projects/new` | Manage owned projects or create a draft. |
| `/my-applications`, `/my-teams` | Application history and current teams. |
| `/projects/:projectId` | Project details and owner controls. |
| `/projects/:projectId/applications` | Owner reviews applicants. |
| `/projects/:projectId/team`, `/projects/:projectId/milestones` | Team roster and milestone progress. |

Project screens require a session. The API client attaches the access token,
refreshes once after a 401, and rejects responses from a previous account.
See the [API contract](../docs/backend-api-contract.md).

## Checks and hosting

Run `npm test`, `npm run lint`, and `npm run build`.

Vercel uses `frontend/` as the project root and currently tracks `backend` for
production. Automatic builds from `backend` are disabled in `vercel.json`, so
publishing is a separate step. The final release will move tracking to `main`.
Deep links are rewritten to `index.html`.

In Supabase Auth, allow `/auth/callback` and `/reset-password` on each frontend
origin you use. Verify real email delivery and both redirects before release.
The hosted API may need updating before the newer screens work online.
