# Project progress — November 16, 2026

The hosted API supports sign-in, profile editing, and project browsing.
The frontend integration is on `backend` for comparison with the `frontend` branch.

- [Frontend site](https://project-hub-client-hazel.vercel.app/)
- [Hosted API documentation](https://project-hub-api-ruby.vercel.app/docs)
- [Frontend API contract](docs/backend-api-contract.md)

## Working features

- Supabase sign-in, session persistence, and sign-out.
- Profile creation/editing with saved roles shown as read-only.
- Project list/detail, search, filters, and pagination.
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

## Checks

- All 133 backend tests, Ruff, and migration checks passed.
- All 28 frontend tests, ESLint, and the production build passed.
- Dependency audit reported no known vulnerabilities.
- Two demo users completed browser checks against the hosted API from localhost.
- Profile edits and zero hours survived reload; original demo values were restored.
- Search, combined catalog filters, pagination, project details, and empty results worked.
- A private draft was visible to its owner and hidden from the other account.
- Account switching showed the correct profile. Sign-out protected direct profile links.
- Automated tests cover expired-token retries, failed refresh, service errors,
  duplicate submissions, and late responses from a previous account.
- Browser error/warning logs were empty.

## Remaining work

Compare the frontend versions and review what to merge into `main`. Profile selections, project
management, applications, and teams follow separately.

The implementation plan remains local and ignored by Git.
