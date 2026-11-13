# Database setup

We use Supabase for the application's shared development database and sign-in.
The backend runs locally and connects to Supabase.

You need Python 3.12 and `uv` to run the backend. Start each section below from
the repository root. Keep existing private environment files; copy an example
only when setting up a new file.

## Connect to Supabase

This machine already has `backend/.env.supabase` configured. On a new machine,
copy `backend/.env.supabase.example` to `backend/.env.supabase` and fill in:

| Setting | What to enter |
| --- | --- |
| `DATABASE_URL` | Session pooler connection from Supabase's Connect screen |
| `DATABASE_PASSWORD` | Database password, kept separate from the URL |
| `SUPABASE_URL` | Project URL, such as `https://YOUR_PROJECT_REF.supabase.co` |

Keep `postgresql+psycopg` at the start of the database URL, use port 5432,
and keep `sslmode=require` to encrypt the connection. The example shows how
to quote the password. The current setup uses a direct or session-pooler
connection, not the transaction pooler.

Then run:

```sh
cd backend
uv sync --locked --python 3.12
PROJECT_HUB_ENV_FILE=.env.supabase uv run alembic upgrade head
PROJECT_HUB_ENV_FILE=.env.supabase uv run alembic current
PROJECT_HUB_ENV_FILE=.env.supabase uv run uvicorn app.main:create_app --factory
```

`alembic upgrade head` brings the database structure up to date.
`alembic current` shows its migration version, currently `cc1194778d46`.
Use one API worker with the small connection pool in the example.
The API documentation is at <http://127.0.0.1:8000/docs>.

Without `PROJECT_HUB_ENV_FILE=.env.supabase`, commands use the local `.env` file.
Variables already exported in your terminal override either file. If switching
databases gives unexpected results, check exported `DATABASE_URL` and
`DATABASE_PASSWORD` values.

## Connect the frontend

The frontend needs these connection settings:

| Setting | Value |
| --- | --- |
| API base URL | `http://127.0.0.1:8000` when running the backend on the same computer |
| Supabase URL | The same project URL as the backend's `SUPABASE_URL` |
| Supabase publishable key | From the project's API Keys settings in Supabase |

Use the publishable key for frontend sign-in. The database password and server-side
secret key belong only in backend configuration. Demo login details are in the
seed operator's private `backend/.demo-accounts.json`.

The API has not been deployed yet. We can both run it locally; a shared API
address will be available after deployment. Your friend's localhost points to
their own computer.

Add the frontend's address to `CORS_ORIGINS` in the backend environment file
you are using. For example:

```dotenv
CORS_ORIGINS='["http://localhost:5173","http://localhost:3000"]'
```

Use the exact address and port, with no trailing slash. Restart the API after
changing this setting.

The frontend signs in through Supabase and sends the access token with requests:

```http
Authorization: Bearer <access_token>
```

The running API needs `SUPABASE_URL` to check tokens. It does not need the
server-side secret used to create demo accounts.

## Add sample data

The sample data is already in Supabase. To add missing demo records again,
run migrations first, then run this from the repository root:

```sh
cd backend

PROJECT_HUB_ENV_FILE=.env.supabase uv run python -m app.demo.seed \
  --expected-project-ref wxycbijrtsofvhgtoxgs
```

For hosted seeding, add `SUPABASE_SECRET_KEY` to the private `.env.supabase` file.
The older `SUPABASE_SERVICE_ROLE_KEY` is also supported. This key is used only by
the seed command and stays out of frontend code.

The script creates fictional accounts, profiles, projects, skills, and interests.
Running it again adds missing records without resetting existing edits or
passwords. Demo passwords are saved in the private, ignored file
`backend/.demo-accounts.json`.

## Run database tests locally

Docker and local PostgreSQL are used only for database tests in this guide.
These tests need a separate, empty local database whose name ends in `_test`.
They change and remove test tables, so never point them at the shared Supabase
database or your application database.

If `backend/.env` does not exist, copy `backend/.env.example` to it for the local
test settings. From the repository root, run:

```sh
docker compose --env-file backend/.env up -d --wait
docker compose --env-file backend/.env exec -T db sh -c 'createdb -U "$POSTGRES_USER" project_hub_test'
cd backend
uv sync --locked --python 3.12
TEST_DATABASE_URL=postgresql+psycopg://project_hub:local_dev_only@localhost:5432/project_hub_test uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

The test URL above uses the local example credentials. Change it if yours differ.
If the test database already exists, skip the `createdb` command and make sure
it is empty. Without `TEST_DATABASE_URL`, database tests are skipped.

## Rules to keep

- Private environment files and demo credentials stay out of Git.
- Use Alembic migrations to change application tables. Do not also manage the
  same tables through Supabase migration tools or recreate them in the dashboard.
- Keep the Data API disabled or application tables unexposed. The frontend reads
  application data through FastAPI.
- Database row protections are enabled. Missing client access policies are
  expected because direct frontend access is blocked.

For the overall backend layout, see [backend architecture](backend-architecture.md).
