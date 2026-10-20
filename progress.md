# Backend progress — October 19, 2026

Hey! The backend foundation is set up now. FastAPI starts and `/health` returns
`{"status":"ok"}`. There aren't any user or project endpoints yet; this round was
just about getting the structure and database ready.

The database has users, profiles, skills, interests, projects, applications,
memberships, milestones, and the tables that link skills/interests to people and
projects. Student projects and faculty research opportunities use the same project
table. Duplicate applications and memberships are blocked by the database.

Everything is set up for local PostgreSQL through Docker Compose. The README has
the commands to install dependencies with uv, start Postgres, run migrations, and
launch the API. Copy `backend/.env.example` to `backend/.env` first. The real env
file stays out of Git.

For Supabase later, the database URL comes from the environment and users have UUID
IDs that we can link to Supabase Auth. We haven't connected to Supabase or added
passwords, login, or JWT handling. Faculty verification is its own field, so choosing
faculty won't count as being verified. RLS is enabled with no client policies yet;
we'll need to add and test those when we decide what the Data API should expose.

All 19 tests passed against a separate local PostgreSQL 17 instance, including
migration rollback/reapply, relationships, constraints, session cleanup, and RLS. Ruff passed too,
and the API responded to a real HTTP request. Docker wasn't installed on the machine
used for development, so the GitHub workflow also checks the Compose setup on Linux.

One thing to keep in mind for later: deleting a user who owns a project is blocked
until their projects are transferred or removed. Also, accepting an application
won't create a membership yet; that belongs in the workflow we'll build next.

The work is split into backend-branch commits. No paid services were added. The
next step is to decide the first feature to build on top of this, probably auth and
profiles before project CRUD.
