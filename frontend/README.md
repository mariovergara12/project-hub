# Project Hub frontend

React, TypeScript, and Vite. The existing login and signup buttons use Supabase Auth.

```sh
npm ci
npm run dev
```

The public Supabase URL and publishable key default to the shared Project Hub
project, so no local backend or environment setup is needed. To use a different
Supabase project, copy `.env.example` to `.env.local` and update the two `VITE_`
settings. These values are public browser configuration. Never add a database
password, Supabase secret key, service-role key, or demo passwords to this repo.

## Sign in and test the API

1. Get a Project Hub demo account's email and password from the backend owner.
2. Log in on the frontend. Invalid credentials stay on the login screen with an
   error. `/main` and `/profile` require a session, including after a page reload.
3. Expand **API testing**, click **Copy API token**, then **Open API docs**.
4. Click **Authorize** in the docs and paste the token without adding `Bearer`.
5. Execute `GET /me` or `GET /projects`. A successful request returns HTTP 200.

Supabase persists and refreshes the frontend session. A token pasted into the
docs does not update automatically: use **Copy API token** again if it expires.
**Log Out** clears this browser's session and returns to the login screen.

**Sign Up** creates a normal Project Hub user. If Supabase requires email
confirmation, check your inbox before logging in. Existing demo accounts are
already confirmed. Never use your Supabase dashboard login here.

## Connect future API features

Import the shared client from `src/lib/supabase.ts`. Retrieve the current session
with `supabase.auth.getSession()` and attach its `access_token` to requests as
`Authorization: Bearer <access_token>`. Read and write application data through
the hosted FastAPI API, rather than querying Supabase tables from the browser.
The API must allow the frontend origin in its CORS settings for browser calls;
the Swagger docs test does not verify that setting.

The project browsing and profile editing screens remain frontend work in
progress. Login does not yet connect their controls to the API.

```sh
npm run build
npm run lint
```
