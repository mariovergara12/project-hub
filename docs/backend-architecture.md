# How the backend works

The backend uses FastAPI to handle requests and PostgreSQL to store data.
Supabase handles sign-in and hosts the shared development database.

## How a request works

1. The user signs in through Supabase.
2. The frontend sends the user's access token to FastAPI.
3. FastAPI checks the token and what the user is allowed to access.
4. The backend reads or updates the database and returns a response.

The frontend gets application data through FastAPI. Direct access to the
application tables through Supabase is blocked.

## Where the code lives

All paths below are inside `backend/`.

| Folder | Purpose |
| --- | --- |
| `app/core` | Settings, database connections, and authentication checks |
| `app/modules/auth` | Checks Supabase access tokens |
| `app/modules/users` | Own-account and profile features |
| `app/modules/projects` | Project browsing and skills/interests lists |
| `app/models` | Defines the database tables and their relationships |
| `app/demo` | Creates fictional development data when run manually |
| `migrations` | Records changes to the database structure |
| `tests` | Checks backend behavior and permissions |

Within a feature, routers handle HTTP requests, services handle application
rules, and repositories handle database queries. Each request gets its own
database session. Services decide when to save changes; unfinished changes are
rolled back when the session closes.

## Available endpoints

All endpoints except `/health` require a Supabase access token.

| Method | Endpoint | What it does |
| --- | --- | --- |
| GET | `/health` | Checks that the API is running; does not check the database |
| GET | `/me` | Returns the signed-in user's account and profile |
| PATCH | `/me/profile` | Creates or updates the user's profile |
| GET | `/projects` | Lists projects the user can see |
| GET | `/projects/{id}` | Returns one project the user can see |
| GET | `/skills` | Lists available skills |
| GET | `/interests` | Lists available interests |

Project lists support search and filters. List responses include a
`next_cursor` value for loading the next page. Full request and response details
are available at `/docs` while the API is running.

## Main data

- Users have a profile, skills, and interests.
- Users can own projects, apply to projects, and join teams.
- Projects have requirements, skills, interests, and milestones.
- Student projects and faculty research opportunities use the same project table.
- User IDs match their Supabase Auth account IDs in the hosted database.

The database prevents duplicate applications and memberships for the same
person and project. Skill and interest names are lowercase and unique.

## Access rules

- Users can view and edit their own profile.
- Signed-in users can browse open projects.
- Other project states are visible only to the owner or existing team members.
- Users cannot change their account role or faculty verification through profile edits.
- A faculty role does not automatically mean the account is verified.

FastAPI enforces these rules. Database protections also block direct frontend
access, but the backend's database connection can bypass those protections.
Every new feature must therefore check permissions in the backend.

The API checks token signatures and expiry. An unexpired token may still work
after logout; the API does not check every request against a live session list.

## Important limits

Deleting a project also removes its related applications, memberships, and
milestones. A user who owns projects cannot be deleted until those projects are
transferred or removed.

Project creation/editing, applications, team management, milestones, and matching
still need working APIs. Accepting an application does not yet create a team
membership automatically.

For connection settings, migrations, tests, and demo data commands, see
[database setup](database-setup.md).
