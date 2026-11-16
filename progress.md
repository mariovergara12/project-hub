# Project progress — November 16, 2026

The hosted API supports sign-in, profile editing, and project browsing.
The frontend integration is on `backend` for comparison with the `frontend` branch.

- [Frontend site](https://project-hub-client-hazel.vercel.app/)
- [Hosted API documentation](https://project-hub-api-ruby.vercel.app/docs)
- [Frontend API contract](docs/backend-api-contract.md)

## Working features

- Supabase sign-in, session persistence, and sign-out.
- Profile creation/editing with saved roles shown as read-only.
- Profile skills/interests can be saved, replaced, and cleared in the local integration.
- A trusted faculty command records role/verification changes with a private audit trail.
- Project list/detail, search, filters, and pagination.
- Local draft creation, owner editing, My Projects, and status changes through archive.
- Owner membership and capacity checks, with a guarded legacy-data backfill.
- Skills and interests catalogs.
- Private projects visible only to owners and team members.
- Loading, empty, signed-out, and failed-request states.
- Bounded authentication refresh/retry and cancellation of stale requests.

## Deployment

The API's CORS setting now includes the hosted frontend and local development
origins. The existing production API was redeployed successfully, and its
frontend preflight returns 200 with the correct allowed origin.

The local frontend starts from `origin/frontend` commit `bca80bc` and adds the
remaining integration. The new screens and frontend CI workflow belong to
`backend`. The `frontend` branch is unchanged. The hosted frontend awaits review
and release.

The frontend configuration skips automatic builds from `backend`.

Profile selections and faculty audit support are included on `backend` for
review before release. Migration `71d9cfa35335` is additive
and has only been applied to isolated local databases. Shared profiles and faculty
assignments are unchanged. See [faculty operations](docs/faculty-operations.md)
for the command and release order.

## Checks

- All 235 backend tests, Ruff, and migration checks passed.
- All 45 frontend tests, ESLint, and the production build passed.
- Dependency audit reported no known vulnerabilities.
- Two demo users completed browser checks against the hosted API from localhost.
- Profile edits and zero hours survived reload; original demo values were restored.
- Search, combined catalog filters, pagination, project details, and empty results worked.
- A private draft was visible to its owner and hidden from the other account.
- Account switching showed the correct profile. Sign-out protected direct profile links.
- Automated tests cover expired-token retries, failed refresh, service errors,
  duplicate submissions, and late responses from a previous account.
- Earlier hosted integration checks had no browser errors or warnings.
- Local browser checks confirmed saved selections after reload, clearing one list
  without changing the other, and separate selections for a second account.
- A local-only faculty command passed dry-run and apply checks; the browser showed
  the resulting role and verification as read-only.
- Tests cover unknown/duplicate/oversized lists, write rollback, concurrent saves,
  role/audit atomicity, audit privacy, and preserving selections when reseeding.

Project management is implemented locally and awaits review. The owner counts
as a member. Migration `9eb18a4d2620` preserves existing memberships and stops if
adding a missing owner would exceed capacity. It has only been applied locally.
See [project management](docs/project-management.md) for release details.

New checks confirmed draft privacy with two real demo sign-ins against the local
API, My Projects isolation, saved/cleared project inputs, published search
visibility, owner-only controls, and progression through read-only archive.
Tests cover invalid transitions, faculty permissions, rollback after a simulated
write failure, and concurrent edits without mixing fields and requirements.
New screens load separately to keep the production build free of size warnings.

## Remaining work

Review the project management changes, apply the reviewed migrations, and
release the API before publishing the updated frontend. Continue comparing the
frontend versions before merging into `main`. Applications and teams follow.

The implementation plan remains local and ignored by Git.
