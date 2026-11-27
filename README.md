# Project Hub

Find a university project, apply to join, and work with your team. Students can
create projects; verified faculty can also post research opportunities.

Built with React, TypeScript, FastAPI, PostgreSQL, and Supabase Auth. Includes
profiles, project search, applications, teams, and milestone tracking.

[Frontend](https://project-hub-client-hazel.vercel.app/) ·
[Hosted API docs](https://project-hub-api-ruby.vercel.app/docs)

These guides describe the `backend` branch. Hosted apps may run older commits.

## Run locally

You need Python 3.12, uv, Node.js 24, npm, and the shared Supabase settings.

**Backend** — from the repository root:

```sh
cd backend
uv sync --locked --python 3.12
cp -n .env.supabase.example .env.supabase
```

Fill in the private `.env.supabase` file with your database connection and
Supabase project URL. Keep credentials out of Git. Review the
[database setup](docs/database-setup.md) and
[migration notes](docs/project-management.md#database-release) before upgrading a shared database.
Then start the API:

```sh
PROJECT_HUB_ENV_FILE=.env.supabase uv run uvicorn app.main:create_app --factory --reload
```

**Frontend** — in a second terminal, from the repository root:

```sh
cd frontend
npm ci
cp -n .env.example .env.local
```

Set the public Supabase URL/key and `VITE_API_BASE_URL=http://localhost:8000`
in `.env.local`, then run `npm run dev`. Open <http://localhost:5173>.
Local API docs are at <http://localhost:8000/docs>.

## Guides and checks

- [API contract](docs/backend-api-contract.md): authentication, endpoints, and errors.
- [Applications and teams](docs/applications-and-teams.md): applying, accepting, and joining.
- [Project management](docs/project-management.md): ownership, statuses, milestones, and migrations.
- [Faculty operations](docs/faculty-operations.md): verify faculty through the operator command.
- [Frontend setup](frontend/README.md): account callbacks, checks, and deployment settings.

Run `npm test`, `npm run lint`, and `npm run build` from `frontend/`.
Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest -q`
from `backend/`. Database tests require a **separate, empty local
PostgreSQL database** via `TEST_DATABASE_URL`; without it, integration tests are skipped.
See [database test setup](docs/database-setup.md).
