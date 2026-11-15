# Project progress — November 14, 2026

The backend supports sign-in, profile editing, and project browsing.
The frontend screens are live and still need to be connected to the API.

- [Frontend site](https://project-hub-client-hazel.vercel.app/)
- [Hosted API documentation](https://project-hub-api-ruby.vercel.app/docs)
- [Frontend API contract](docs/backend-api-contract.md)

## Working features

- Supabase sign-in and backend token checks.
- Viewing and editing the signed-in user's profile.
- Project list/detail, search, filters, and pagination.
- Skills and interests catalogs.
- Private projects visible only to owners and team members.
- Separate frontend deployment from the `frontend` branch.

## Sample data

The shared development database contains 10 demo accounts, 10 projects,
12 skills, and 7 interests. Six projects are open.
The seed command adds missing records without resetting edits or passwords.
Demo credentials stay in a private local file.

## Checks

- All 133 backend tests passed, including 14 API contract checks.
- Ruff and migration upgrade/downgrade and drift checks passed.
- Tests used a separate local PostgreSQL database; no shared migrations were applied.
- Two demo accounts signed in, saved and reloaded unchanged profile data,
  and browsed projects and paginated catalogs through the hosted API.
- Private projects were hidden from unrelated users.
- Existing hosted request/response schemas match the local contract.

See [database setup](docs/database-setup.md) for test commands.

## Remaining work

- Add the hosted frontend origin to the API's deployed CORS settings.
  The latest check returned `400 Disallowed CORS origin`.
- Connect frontend sign-in, profiles, and project browsing.
- Check the browser flow with two accounts, including session expiry and sign-out.
- Add profile selections, project management, applications, and teams.

Backend changes go to `backend` first. Production deployment is separate.
