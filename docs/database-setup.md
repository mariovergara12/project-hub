# Database connections

Local PostgreSQL remains the default. Supabase is selected explicitly for each
command; changing the database does not change application services or models.

## Local development

From the repository root, copy `backend/.env.example` to `backend/.env` if you
haven't already, then start PostgreSQL:

```sh
docker compose --env-file backend/.env up -d --wait
cd backend
uv sync --locked --python 3.12
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload
```

## Supabase development database

Copy `backend/.env.supabase.example` to `backend/.env.supabase`. Use the session
pooler connection details from **Connect** in the Supabase dashboard. Keep the
`postgresql+psycopg` driver prefix, port 5432, and `sslmode=require`.

Store the database password in `DATABASE_PASSWORD` in that private file. This
overrides a password in `DATABASE_URL` using SQLAlchemy's URL object, so characters
such as `@`, `%`, and `#` do not need URL encoding. Use dotenv quoting as shown in
the example; escape embedded single quotes with a backslash. Do not paste the
password into chat, command-line arguments, or tracked files.

The real `.env` and `.env.supabase` are ignored by Git; only the examples are
tracked. The private hosted file created during setup has owner-only permissions.
Environment variables override the selected file. If you previously exported
`DATABASE_URL` or `DATABASE_PASSWORD`, unset those before switching databases.

From `backend/`, select the hosted file explicitly:

```sh
PROJECT_HUB_ENV_FILE=.env.supabase uv run alembic upgrade head
PROJECT_HUB_ENV_FILE=.env.supabase uv run alembic current
PROJECT_HUB_ENV_FILE=.env.supabase uv run uvicorn app.main:create_app --factory
```

Without `PROJECT_HUB_ENV_FILE`, the application and Alembic load only `.env`.
Supabase's configured pool is limited to two connections per process, with no
overflow. Use one worker initially and avoid running many processes at once.

`sslmode=require` encrypts the connection and refuses a plaintext fallback. For
server identity verification, use `sslmode=verify-full` with the trusted root
certificate configuration provided by Supabase. The application rejects Supabase
URLs with missing SSL settings or modes that permit plaintext.

Alembic owns application migrations. Do not manually recreate application tables
in the Table Editor or manage the same tables with Supabase migration tooling.
Keep the Data API disabled. RLS is enabled by the initial migration without any
client access policies. The database owner can bypass RLS; authentication and
request authorization are separate future work.

Run integration tests against a separate **local** empty database ending in
`_test`, using `TEST_DATABASE_URL`. Never run the destructive integration fixture
against the hosted project.

References: [Supabase connection methods](https://supabase.com/docs/guides/database/connecting-to-postgres),
[SSL modes](https://supabase.com/docs/guides/platform/ssl-enforcement).
