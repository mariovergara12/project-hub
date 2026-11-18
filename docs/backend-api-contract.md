# Frontend API contract

This describes the API on the backend branch. The hosted API may be running an
older version. Use `/docs` on the API you connect to for its request schemas.

| Address | URL |
| --- | --- |
| Hosted API | <https://project-hub-api-ruby.vercel.app> |
| API documentation | <https://project-hub-api-ruby.vercel.app/docs> |
| OpenAPI schema | <https://project-hub-api-ruby.vercel.app/openapi.json> |
| Hosted frontend | <https://project-hub-client-hazel.vercel.app> |

## Send authenticated requests

Sign in through Supabase, then send the session's access token with each request:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

`Content-Type` is needed when sending JSON. The API does not use frontend cookies.
All routes below require a token. `/health`, `/docs`, and `/openapi.json` are public.

If a request returns 401, refresh the session and retry once. If that fails,
return to sign-in. For 503, show an error and let the user retry. Clear saved
account data when signing out or switching accounts.

IDs are UUID strings. Replace placeholders such as `<skill-id>` with real IDs
from the API. Dates and times use ISO 8601 strings.

## Account and profile

`GET /me` returns the signed-in account:

```json
{
  "id": "<user-id>",
  "role": "student",
  "faculty_verified_at": null,
  "profile": null,
  "skills": [],
  "interests": []
}
```

`role` is `student`, `faculty`, or `administrator`. Verified faculty must have
both the faculty role and a non-null `faculty_verified_at`.
`profile: null` means the user has not created a profile.
Skills and interests contain `{id, name}` objects, sorted by name.

`PATCH /me/profile` creates or edits the profile and returns the profile directly.
For example:

```json
{"display_name":"Maya Chen","availability_hours":0}
```

| Field | Allowed value |
| --- | --- |
| `display_name` | 1–150 characters; required when creating a profile |
| `university` | 1–200 characters or null |
| `major`, `department` | 1–150 characters or null |
| `bio` | Up to 5,000 characters or null; empty string allowed |
| `learning_goals` | Up to 2,000 characters or null; empty string allowed |
| `availability_hours` | Integer 0–168 or null |
| `experience_years` | Integer 0–100 or null |

Text is trimmed before validation. Omit a field to keep its saved value. Send
null to clear an optional field. `display_name` cannot be null, even if the
OpenAPI input schema shows it as nullable. Zero is a valid numeric value.
Numeric strings and booleans are rejected for integer fields.

An empty PATCH leaves an existing profile unchanged. Creating a profile without
a name returns 422. The response also includes the read-only `user_id`.
Unknown fields, including `role` and `faculty_verified_at`, return 422.
Role changes use the [faculty operator command](faculty-operations.md).

### Save skills and interests

| Method | Endpoint | Request | Response |
| --- | --- | --- | --- |
| PUT | `/me/skills` | `{"skill_ids":["<skill-id>"]}` | `{"skills":[{"id":"<skill-id>","name":"react"}]}` |
| PUT | `/me/interests` | `{"interest_ids":["<interest-id>"]}` | `{"interests":[{"id":"<interest-id>","name":"robotics"}]}` |

Each request replaces one list. An empty array clears it. Use up to 50 unique,
known catalog IDs. Missing lists, null, duplicates, unknown IDs, and extra fields
return 422. A failed save leaves the previous list intact. Saving skills does
not change interests or profile fields. `GET /me` returns the saved selections.

## Browse projects and catalogs

| Method | Endpoint | Result |
| --- | --- | --- |
| GET | `/projects` | Projects the caller can see |
| GET | `/projects/{id}` | One project |
| GET | `/skills` | Skill IDs and names |
| GET | `/interests` | Interest IDs and names |

Open projects are visible to every signed-in user. Draft, in-progress, completed,
and archived projects are visible only to their owner and current members.
A hidden or missing project returns 404.

Project lists contain the same project fields as the detail route:

| Field | Meaning |
| --- | --- |
| `id`, `title`, `description` | Project ID and text |
| `project_type` | `student_project` or `research_opportunity` |
| `status` | `draft`, `open`, `in_progress`, `completed`, or `archived` |
| `weekly_hours`, `minimum_experience_years` | Integer or null when unspecified |
| `max_members` | Integer or null when no limit is set |
| `member_count` | Number of members, including the owner |
| `owner` | Public user summary: `{id, display_name, role, faculty_verified}` |
| `skills` | `{id, name, required}` objects, sorted by name |
| `interests` | `{id, name}` objects, sorted by name |
| `created_at`, `updated_at` | Timestamps |

A public user summary excludes email and private profile fields.
`display_name` can be null. Empty skill and interest lists are returned as `[]`.
Existing projects need the owner-membership migration before hosted member
counts include their owners.

### Project filters

`GET /projects` accepts these optional filters:

| Parameter | Meaning |
| --- | --- |
| `q` | Search title and description; 1–200 characters, case-insensitive |
| `project_type`, `status` | Match one of the values listed above |
| `skill_id` | Match a required or optional skill |
| `interest_id` | Match an interest |

Filters combine: a project must match all supplied filters and be visible to the
caller. Without a status filter, the list includes all visible statuses.
Search trims whitespace; whitespace alone means no search. `%` and `_` are
ordinary characters. Unknown catalog IDs return an empty list; malformed IDs
return 422.

### Load another page

List routes return `items` and `next_cursor`:

```json
{"items":[],"next_cursor":null}
```

Use `limit` to set the page size: 1–100, default 20. Start without `cursor`, then
send the previous response's `next_cursor` to get another page. Null means there
are no more pages. Omit the cursor rather than sending the text `null`.
Keep filters the same between pages and reset the cursor when they change.

Projects and catalog entries sort by UUID, not by name or date. Catalog entries
contain only `id` and `name`. Lists can change between requests as records change.

## Create and manage projects

| Method | Endpoint | Action |
| --- | --- | --- |
| POST | `/projects` | Create a draft; returns 201 |
| PATCH | `/projects/{id}` | Edit project fields and requirements |
| PATCH | `/projects/{id}/status` | Change status, for example `{"status":"open"}` |
| GET | `/me/projects` | List projects owned by the caller |

Only the owner can edit a project or change its status. The API takes ownership
from the access token. Requests cannot set an owner, project ID, or status through
project creation or editing. Successful writes return the project.

| Field | Allowed value |
| --- | --- |
| `title` | 1–200 trimmed characters; required for creation |
| `description` | 1–10,000 trimmed characters; required for creation |
| `project_type` | Defaults to `student_project` |
| `weekly_hours` | Integer 0–168 or null |
| `minimum_experience_years` | Integer 0–100 or null |
| `max_members` | Integer 1–100 or null for no limit; includes the owner |
| `skills` | Up to 50 unique entries: `{"skill_id":"<skill-id>","required":true}` |
| `interest_ids` | Up to 50 unique, known interest IDs |

`required` defaults to true and must be a boolean. Skill IDs must exist in the
catalog. New projects default to empty skill and interest lists. On edits, omit
a field to keep it, send an empty array to clear a list, or send null to clear a
numeric field. Other fields cannot be null. All changes save together or fail
together. Capacity cannot be reduced below the current member count.

The owner joins the team when the project is created. Creating, editing, or
publishing research opportunities requires verified faculty. An owner who loses
verification can still convert the project to a student project or archive it.

Statuses follow `draft → open → in_progress → completed`. Any non-archived status
can become `archived`. Sending the current status again changes nothing. Other
transitions return 409. Archiving cannot be undone through the API, and archived
project details cannot be edited. Starting an open project makes it private to
the owner and members.

`GET /me/projects` supports `limit`, `cursor`, and `status`. It includes owned
drafts and archived projects. Being a member of someone else's project does not
put it in this list.

## Applications and teams

| Method | Endpoint | Action |
| --- | --- | --- |
| POST | `/projects/{id}/applications` | Apply with `{"message":"..."}`; message is optional |
| GET | `/me/applications` | View the caller's application history |
| PATCH | `/applications/{id}/withdraw` | Withdraw a pending application |
| GET | `/projects/{id}/applications` | Owner reviews applications |
| PATCH | `/applications/{id}/decision` | Owner sends `{"status":"accepted"}` or `{"status":"rejected"}` |
| GET | `/projects/{id}/members` | Owner and members view the team |
| DELETE | `/projects/{id}/members/{user_id}` | Owner removes a member, or a member leaves |

### Apply and review

Application messages allow up to 2,000 trimmed characters. The message can be
omitted or null. The API takes the applicant from the access token. A new
application returns 201. Only the applicant and project owner can see its message.

The project must be open and have space to apply or accept someone. The owner
counts toward capacity. Owners and existing members cannot apply.
Each person has one application per project.

| Application status | What can happen next |
| --- | --- |
| `pending` | The owner can accept/reject it; the applicant can withdraw it |
| `withdrawn` | The applicant can resubmit if the project is open and has space |
| `accepted` | The decision stays in history after leaving or removal; rejoining is unavailable |
| `rejected` | Resubmission is unavailable |

Resubmission returns 200, reuses the application ID and creation date, and replaces
the message. Repeating the same withdrawal or decision changes nothing. Changing
a final decision returns 409. Acceptance saves the decision and membership
together; a full-team error leaves the application pending.

Application responses contain `id`, `project`, `applicant`, `message`, `status`,
`created_at`, and `updated_at`. `project` contains `id`, `title`, `status`, and
`owner_id`. `applicant` is a public user summary.

Both application lists support `limit`, `cursor`, and `status`, ordered by
application UUID. My Applications also accepts `project_id`. Owner review adds a
`project` summary to the page response. Application history does not grant access
to private project details or the team roster.

### View or leave a team

The roster returns `project`, `max_members`, `member_count`, `items`, and
`next_cursor`. Each item contains `user` (a public user summary), `joined_at`, and
`is_owner`. Use `limit` and `cursor` to load more members. Members sort by user
UUID, which is also the roster cursor.

Only the owner can remove another member. The owner cannot leave or be removed.
Removal returns `{"project_id":"...","user_id":"...","removed":true}`. If the
owner repeats removal, it returns `removed:false`. Leaving ends member access;
a former member can receive 404 when opening a private project or roster.
Repeating an old acceptance does not add that person back to the team.

Archived projects allow history and roster reads, and applicants can still
withdraw pending applications. New decisions and membership changes are blocked.

## Handle errors

Read the response's `detail` field. It is usually a message:

```json
{"detail":"The project team is full"}
```

Field validation returns a list instead:

```json
{"detail":[{"loc":["body","title"],"msg":"...","type":"..."}]}
```

| Status | Meaning |
| --- | --- |
| 401 | Missing, invalid, or expired token; or the Auth account no longer exists |
| 403 | The account cannot perform this action |
| 404 | The record is missing or hidden from this account |
| 409 | The action conflicts with the current status, membership, or capacity |
| 422 | Invalid fields, unknown catalog IDs, or invalid query parameters |
| 503 | Authentication is not configured or the identity provider is unavailable |

Some server errors may not return JSON. Show a useful error message in that case.
Administrator accounts do not bypass project, application, or team permissions.

## CORS

The backend allows GET, POST, PATCH, PUT, and DELETE from configured origins.
Authorization and Content-Type headers are allowed; cookies are not needed.
Use exact origins without a trailing slash:

```dotenv
CORS_ORIGINS='["http://localhost:5173","http://localhost:3000","https://project-hub-client-hazel.vercel.app"]'
```

Add preview origins individually when they are needed.
