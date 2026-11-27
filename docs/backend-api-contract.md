# Backend API contract

This is a quick reference for the `backend` branch. For full request fields,
validation limits, and response schemas, use `/docs` or `/openapi.json` on the API
you connect to. The hosted API may run an older commit.

- Local API: <http://localhost:8000/docs>
- Hosted API: <https://project-hub-api-ruby.vercel.app/docs>

## Shared rules

Sign in with Supabase and send `Authorization: Bearer <access_token>` on every
route below. Send `Content-Type: application/json` for JSON bodies. Cookies are
not used. `/health`, `/docs`, and `/openapi.json` are public.

- IDs are UUID strings. Timestamps use ISO 8601; milestone due dates use `YYYY-MM-DD`.
- Text is trimmed. Unknown JSON body fields are rejected. Do not send role or owner overrides.
- On PATCH, omitted fields stay unchanged. Use `null` only where the schema allows it.
- Lists return `items` and `next_cursor`. Use `limit` (1–100, default 20) and send the previous `next_cursor` to load more. `null` means the end.
- Reset the cursor when filters change. Lists sort by UUID, not name or date; roster cursors use member **user IDs**.
- Public user summaries contain `id`, `display_name` (possibly null), `role`, and `faculty_verified`. They exclude email and private profile fields.

## Account and catalogs

| Method | Route | Input or result |
| --- | --- | --- |
| GET | `/me` | Account ID, role, verification, profile, skills, and interests. |
| PATCH | `/me/profile` | Create/edit profile; returns the profile directly. |
| PUT | `/me/skills` | `{"skill_ids":["UUID"]}` → `{"skills":[{"id":"UUID","name":"react"}]}` |
| PUT | `/me/interests` | `{"interest_ids":["UUID"]}` → `{"interests":[{"id":"UUID","name":"robotics"}]}` |
| GET | `/skills` | Paginated `{id, name}` catalog entries. |
| GET | `/interests` | Paginated `{id, name}` catalog entries. |

`GET /me` returns `profile: null` until a profile is created. Creating a profile
requires `display_name` (1–150 characters); the name cannot be null. Optional
fields are `university`, `major`, `department`, `bio`, `learning_goals`,
`availability_hours` (0–168), and `experience_years` (0–100). Integer fields reject
strings and booleans; zero is valid. Role/verification changes use the
[faculty operator](faculty-operations.md), not profile edits.

Each selection PUT replaces its list. Use up to 50 unique, known catalog IDs;
`[]` clears the list. Missing/null lists, duplicates, and unknown IDs return 422.
A failed replacement leaves the saved list unchanged.

## Projects

| Method | Route | Action |
| --- | --- | --- |
| GET | `/projects` | List visible projects. Filters: `q`, `project_type`, `status`, `skill_id`, `interest_id`. |
| GET | `/projects/{project_id}` | Read one visible project. |
| GET | `/me/projects` | List owned projects; accepts `status`. |
| POST | `/projects` | Create a draft with `title` and `description`; returns 201. |
| PATCH | `/projects/{project_id}` | Owner edits fields and requirements. |
| PATCH | `/projects/{project_id}/status` | Owner sends `{"status":"open"}` or another allowed next status. |

Open projects are visible to every signed-in user. Other statuses require
ownership or current membership. Filters never grant access. Search matches a
literal, case-insensitive substring of title/description; supplied filters combine.

Project responses include text/type/status, hours/experience/capacity,
`member_count` (including the owner), a public `owner` summary, `skills`
(`id`, `name`, `required`), `interests` (`id`, `name`), and timestamps.
Optional numeric fields can be null; catalogs and selections use arrays.
See [project management](project-management.md) for editing rules and lifecycle.

## Applications and teams

| Method | Route | Action |
| --- | --- | --- |
| POST | `/projects/{project_id}/applications` | Apply with optional `{"message":"..."}`. Returns 201, or 200 when resubmitting. |
| GET | `/me/applications` | Own application history. Filters: `status`, `project_id`. |
| PATCH | `/applications/{application_id}/withdraw` | Applicant withdraws a pending application; send `{}`. |
| GET | `/projects/{project_id}/applications` | Owner reviews applications; accepts `status`. |
| PATCH | `/applications/{application_id}/decision` | Owner sends `{"status":"accepted"}` or `{"status":"rejected"}`. |
| GET | `/me/teams` | Current memberships and owned projects; accepts project `status`. |
| GET | `/projects/{project_id}/members` | Owner/current members read the roster. |
| DELETE | `/projects/{project_id}/members/{member_id}` | Owner removes a member, or a member leaves. `member_id` is the user's UUID. |

Application responses contain `id`, `project`, `applicant`, `message`, `status`,
and timestamps. The project summary contains `id`, `title`, `status`, `owner_id`.
Owner review adds that summary to its page response.

`/me/teams` items contain a full `project`, `joined_at` (nullable for legacy owners),
and `is_owner`. The roster adds `project`, `member_count`, and `max_members` to
its page; each member contains `user`, `joined_at`, and `is_owner`.
Removal returns `{project_id, user_id, removed}` with 200, not an empty body.
See [applications and teams](applications-and-teams.md) for status and access rules.

## Milestones

| Method | Route | Action |
| --- | --- | --- |
| GET | `/projects/{project_id}/milestones` | Team-only list; accepts milestone `status`. |
| POST | `/projects/{project_id}/milestones` | Create a milestone; returns 201. |
| PATCH | `/milestones/{milestone_id}` | Edit fields or status. At least one field is required. |
| DELETE | `/milestones/{milestone_id}` | Delete; returns **204 with no body**. Do not parse JSON. |

Fields: `title` (1–200 characters), optional `description` (up to 10,000), optional
`due_date` (`YYYY-MM-DD`), and `status` (`todo`, `in_progress`, `completed`). Creation
requires a title and defaults to `todo`. On PATCH, null clears description/date,
but title/status cannot be null. Responses add IDs and timestamps.

Lists add a `project` summary and `progress` (`total`, `todo`, `in_progress`,
`completed`). Progress covers all project milestones regardless of filtering or
pagination. Completed/archived projects are read-only; former members have no access.

## Errors and CORS

Read `detail`: usually a message, or a list of field errors with `loc`, `msg`, and
`type`. Handle non-JSON server errors too. Never retry writes automatically after
an uncertain network failure.

| Status | Meaning |
| --- | --- |
| 401 | Missing/invalid session or deleted Auth account. Refresh and retry once, then sign in again if needed. |
| 403 / 404 | Action is forbidden, or the record is missing/hidden. |
| 409 | Status, membership, or capacity conflict. Refresh the affected data. |
| 422 | Invalid body, catalog IDs, or query parameters. |
| 503 | Authentication configuration/provider is unavailable. Offer a retry. |

Administrator accounts do not bypass project/team permissions. CORS allows GET,
POST, PATCH, PUT, and DELETE from exact origins in `CORS_ORIGINS` (no trailing
slash), with Authorization and Content-Type headers. Add preview origins explicitly.
