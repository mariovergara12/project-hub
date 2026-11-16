# Project Hub

A university collaboration platform connecting students and faculty through interdisciplinary projects and research opportunities.

The backend uses FastAPI, SQLAlchemy, PostgreSQL, and Supabase Auth.

- [Frontend site](https://project-hub-client-hazel.vercel.app/)
- [Hosted API documentation](https://project-hub-api-ruby.vercel.app/docs)
- [Supabase setup and local tests](docs/database-setup.md)
- [Backend architecture](docs/backend-architecture.md)
- [Frontend API contract](docs/backend-api-contract.md)
- [Faculty operations](docs/faculty-operations.md)
- [Current progress](progress.md)

After configuring `backend/.env.supabase`, run from `backend/`:

```sh
uv sync --locked --python 3.12
PROJECT_HUB_ENV_FILE=.env.supabase uv run alembic upgrade head
PROJECT_HUB_ENV_FILE=.env.supabase uv run uvicorn app.main:create_app --factory --reload
```

Interactive API documentation is available at <http://127.0.0.1:8000/docs>.

To run the frontend, follow [frontend setup](frontend/README.md).
