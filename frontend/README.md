# Project Hub frontend

React, TypeScript, Vite, and Supabase Auth. Application data comes from FastAPI.

## Run locally

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` to the shared
project's public settings. `VITE_API_BASE_URL` defaults to
`https://project-hub-api-ruby.vercel.app`.
The existing Supabase client also defaults to the shared development project.
Never put server-side keys, database passwords, or demo passwords in these files.

The API allows `http://localhost:5173` and `http://localhost:3000`.
Use either origin when testing locally.

## Available screens

- `/`: sign in or sign up through Supabase.
- `/main`: browse projects, search, filter by type/status/skill/interest, and paginate.
- `/projects/:projectId`: project details, owner summary, requirements, and capacity.
- `/profile`: create or edit your profile and view the server's role/verification.

The updated profile also saves selected skills and interests through their own
buttons. It requires the updated backend endpoints, currently pending release.
Local verification uses an isolated API/database; hosted application data is unchanged.

Protected screens require a session. Logging out removes account data from the
screen. A single API helper attaches the current access token, handles both
FastAPI error formats, and allows at most one refresh/retry after a 401.
Requests are cancelled when filters or accounts change.

Project management and applications are not available yet.

## Checks

```sh
npm test
npm run lint
npm run build
npm audit
```

Tests cover authentication retries, account changes, catalog pagination, profile
creation/save errors, duplicate submissions, and stale responses.

## Hosting

The Vercel frontend project uses `frontend/` as its root and deploys its
`frontend` production branch. `vercel.json` disables automatic frontend builds
from `backend` and preserves deep-link rewrites.

Browser verification of the new screens used this local frontend with the hosted
API. Compare this version with the `frontend` branch before publishing new screens.
