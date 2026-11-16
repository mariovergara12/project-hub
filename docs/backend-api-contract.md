# Frontend API contract

Checked against the hosted API and backend source on November 16, 2026.
This covers the existing sign-in, profile, project browsing, and catalog features.
Profile selection endpoints and the audit migration below are pending review and
release. Their browser checks use the local API and a separate local database.

## Connection and identity

| Setting | Value |
| --- | --- |
| Hosted API | `https://project-hub-api-ruby.vercel.app` |
| Interactive documentation | <https://project-hub-api-ruby.vercel.app/docs> |
| Machine-readable contract | <https://project-hub-api-ruby.vercel.app/openapi.json> |
| Hosted frontend origin | `https://project-hub-client-hazel.vercel.app` |

The frontend signs in with Supabase using the public URL and publishable key
from the existing private handoff. It sends the current session's **access token**
to FastAPI as `Authorization: Bearer <access_token>`. Send `Content-Type:
application/json` for profile updates. The API does not use frontend cookies or
accept a user ID as proof of identity. All feature routes below require a token;
`GET /health`, `/docs`, and `/openapi.json` are public.

Use one frontend API helper and the Supabase client's session refresh support.
On 401, allow at most one refresh and retry of a request. If refresh fails or the
retry returns 401, return to the signed-out state. A 503 is an unavailable service;
show a retry state without signing the user out or starting a refresh loop.
Clear cached account data when switching accounts or signing out.
Supabase documents the access-token and refresh-token lifecycle in
[User sessions](https://supabase.com/docs/guides/auth/sessions).

API token checks validate signature, issuer, audience, expiry, and the signed
subject. Account roles come from the application database. An unexpired token
can remain valid after sign-out; the frontend must discard its session and data.

## Account and profile

`GET /me` returns these fields, including nullable fields:

```json
{
  "id": "<signed-in-user-uuid>",
  "role": "student",
  "faculty_verified_at": null,
  "profile": null,
  "skills": [],
  "interests": []
}
```

The example uses a placeholder UUID. `role` is `student`, `faculty`, or
`administrator`. `faculty_verified_at` is an ISO 8601 timestamp or null. A faculty
role alone does not establish verification. `profile: null` means the user has
not created a profile; show the profile creation form. The updated backend adds
`skills` and `interests` as arrays of `{id, name}`, sorted by name. Empty arrays
mean no selections. Existing fields keep their names and meanings.

`PATCH /me/profile` creates or partially updates the current user's profile.
On success it returns the profile object directly, rather than the `/me` wrapper.
All fields in the response below are present. Omitted PATCH fields retain their
saved values. Explicit null clears any optional field; it cannot clear
`display_name`. Text input is trimmed before validation.

| Field | Response type | PATCH validation |
| --- | --- | --- |
| `user_id` | UUID string | Read-only; never send it |
| `display_name` | string | Required for creation; 1–150 characters; cannot be null |
| `university` | string or null | 1–200 characters when non-null |
| `major` | string or null | 1–150 characters when non-null |
| `department` | string or null | 1–150 characters when non-null |
| `bio` | string or null | At most 5,000 characters; empty string allowed |
| `availability_hours` | integer or null | 0–168; booleans and numeric strings rejected |
| `learning_goals` | string or null | At most 2,000 characters; empty string allowed |
| `experience_years` | integer or null | 0–100; booleans and numeric strings rejected |

For example, `{"display_name":"Maya Chen","availability_hours":0}` can create a
profile. A subsequent `{"bio":null}` clears only the bio. An empty object is a
no-op for an existing profile; it returns 422 when no profile exists because
creation requires a name. Zero hours and zero years are valid saved values;
preserve them in forms.

Unknown fields are rejected with 422, including `role`, `faculty_verified_at`,
`user_id`, `skills`, and `interests`. The input schema currently marks
`display_name` as nullable even though runtime validation rejects explicit null;
the rule above and the endpoint description specify its actual behavior.

## Profile skills and interests

These endpoints are implemented locally and await release:

| Method | Endpoint | Request | Response |
| --- | --- | --- | --- |
| PUT | `/me/skills` | `{"skill_ids":["<catalog-uuid>"]}` | `{"skills":[{"id":"<uuid>","name":"react"}]}` |
| PUT | `/me/interests` | `{"interest_ids":["<catalog-uuid>"]}` | `{"interests":[{"id":"<uuid>","name":"robotics"}]}` |

Each request replaces only that signed-in user's selected list. Send an empty
array to clear it. Up to 50 unique catalog IDs are allowed; names, duplicate IDs,
unknown IDs, malformed UUIDs, missing lists, null, and extra fields return 422.
Unknown IDs use a string `detail`; schema errors use the usual array format.

The full replacement commits in one transaction. Invalid or failed requests leave
the previous selection intact. Repeating a request gives the same saved list.
Concurrent saves for one user run in sequence. Profile fields, roles, and the
other catalog's selection are preserved. `GET /me` returns the saved choices
after reload. There is no route for editing another user's choices.

The frontend saves skills and interests separately and keeps unsaved choices
after a failed request. Catalog creation and account roles remain unavailable
through profile requests. Faculty changes use a
[trusted operator command](faculty-operations.md).

## Project list and detail

`GET /projects` returns `{"items":[<project>],"next_cursor":<UUID or null>}`.
`GET /projects/{project_id}` returns one project with the same fields as a list
item. The detail URL does not use a different wrapper.

| Field | Response type / meaning |
| --- | --- |
| `id` | Project UUID string |
| `title`, `description` | Strings |
| `project_type` | `student_project` or `research_opportunity` |
| `status` | `draft`, `open`, `in_progress`, `completed`, or `archived` |
| `weekly_hours` | Integer or null; null means unspecified |
| `minimum_experience_years` | Integer or null; null means unspecified |
| `max_members` | Integer or null; null means no configured cap |
| `member_count` | Integer; number of saved membership rows |
| `owner` | `{id, display_name, role, faculty_verified}` |
| `skills` | Array of `{id, name, required}`; empty array when absent |
| `interests` | Array of `{id, name}`; empty array when absent |
| `created_at`, `updated_at` | ISO 8601 timestamps |

`owner.id` is a UUID; `owner.display_name` can be null when no profile exists.
`owner.role` uses the same role values as `/me`. `owner.faculty_verified` is a
boolean, rather than a timestamp. Owner summaries exclude email, bio, and private
profile details. Linked skills/interests are sorted by name within a project.

The current seed has no memberships, so its projects report `member_count: 0`.
Ownership does not currently create a membership. Confirm whether owners should
count as members before building project creation.

Every signed-in user can see open projects. Other statuses are visible only to
their owner or an existing member. Without a status filter, the list includes
**all visible statuses**, including the caller's own private projects. Pass
`status=open` when a screen specifically needs open projects. A status filter
does not bypass visibility. Hidden and nonexistent detail IDs both return 404.

### Search and filters

| Query parameter | Accepted value | Behavior |
| --- | --- | --- |
| `limit` | Integer 1–100; default 20 | Maximum items per page |
| `cursor` | UUID string | Exclusive position after the previous page |
| `q` | 1–200 characters | Case-insensitive literal substring of title or description |
| `project_type` | Either project type above | Exact match |
| `status` | Any project status above | Exact match within visible projects |
| `skill_id` | Catalog skill UUID | Matches required or optional linked skills |
| `interest_id` | Catalog interest UUID | Matches linked interests |

All supplied filters combine with AND. Search trims surrounding whitespace;
a whitespace-only search acts like no search. An empty string is invalid.
`%` and `_` are literal search characters, not SQL wildcards. Unknown, valid
catalog UUIDs return an empty page. Malformed UUIDs, unknown enum values, invalid
limits, and oversized search strings return 422.

### Pagination for projects and catalogs

`GET /skills` and `GET /interests` support only `limit` and `cursor`. Both return
`{"items":[{"id":"<uuid>","name":"<name>"}],"next_cursor":null}`.
Catalog names are lowercase. A catalog selection must use its ID.

All three lists sort by UUID ascending, rather than name, date, or relevance.
Start without `cursor`, then pass the returned `next_cursor` unchanged. Keep the
same filters when fetching another page. A cursor is a UUID position, so it does
not need to identify an existing record and is not tied to a server-side session.
Reset pagination when filters change. No total count is returned.

`next_cursor: null` means pagination is finished, including when a final page
contains exactly `limit` items. An empty result is always
`{"items":[],"next_cursor":null}`. Do not send `cursor=null` or an empty cursor
string; omit the parameter. Concurrent data changes can change subsequent pages;
the cursor does not provide a snapshot of the database.

## Errors

Read the HTTP status and FastAPI's `detail` property. Ordinary errors use a string;
field validation uses an array. Both of these are real 422 formats:

```json
{"detail":"display_name is required to create a profile"}
```

```json
{"detail":[{"loc":["body","display_name"],"msg":"...","type":"..."}]}
```

Validation entries can also include `input` and `ctx`; do not depend on exact
Pydantic wording or display raw input values to other users.

| HTTP status | Current meaning / response |
| --- | --- |
| 401 | `Invalid or missing access token`, including expired tokens; `WWW-Authenticate: Bearer` is sent |
| 401 | `Account no longer exists` when the verified identity was deleted; no refresh loop |
| 404 | `Project not found` for hidden or nonexistent project UUIDs |
| 422 | Invalid input; `detail` is an array, or the missing-profile-name string above |
| 503 | `Authentication is not configured` or `Identity provider is unavailable` |

The current endpoints do not return 403/409. New endpoints will document their
errors separately. Unexpected server failures may have a non-JSON body;
the frontend helper should still present a failed-request state.

## CORS

The hosted API now permits the frontend origin. Its CORS setting was updated
for Production and Preview, and the existing production API was redeployed.
The hosted frontend's PATCH preflight returned 200 with the correct allowed
origin. The configured value is:

```dotenv
CORS_ORIGINS='["http://localhost:5173","http://localhost:3000","https://project-hub-client-hazel.vercel.app"]'
```

Use exact origins without a trailing slash. The hosted API currently permits
GET/PATCH; the updated backend adds PUT for selections. Deploy that backend
before publishing the updated selectors. Authorization/Content-Type are allowed;
no cookie credentials are needed. Preview origins
must be added individually when needed.

## Browser checks

These checks passed using the local frontend against the hosted API with two
demo accounts. Repeat them on the hosted frontend after release:

1. Sign in, read the account, create/update a profile, and reload saved values.
2. Browse list/detail, use catalog filters, and load subsequent pages.
3. View a private draft as its owner; verify it stays hidden from the other user.
4. Exercise loading, empty, signed-out, and failed-request states; block repeat
   form submission while a request is running.
5. Exercise expiry with bounded refresh/retry, failed refresh, sign-out, and
   switching accounts without showing the previous user's cached profile.
