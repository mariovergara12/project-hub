# Project progress — November 17, 2026

The backend branch contains the integrated frontend for comparison with the
frontend branch. Applications and teams are implemented locally for review.

- [Hosted frontend](https://project-hub-client-hazel.vercel.app/)
- [Hosted API documentation](https://project-hub-api-ruby.vercel.app/docs)
- [Frontend API contract](docs/backend-api-contract.md)

## Working features

- Supabase sign-in, refresh, account isolation, and sign-out.
- Profile editing and saved skills/interests; roles remain read-only in the UI.
- Trusted faculty operations with a private audit trail.
- Project browsing, filters, pagination, creation, editing, and My Projects.
- Owner-only status changes through read-only archive; owners count toward capacity.
- Application submission, withdrawal, resubmission, and private history.
- Owner acceptance/rejection and team rosters with leave/remove controls.
- Atomic acceptance, capacity checks, protected owners, and accepted history after leaving.

## Checks

- All 271 backend tests, Ruff, and migration checks passed.
- All 63 frontend tests, ESLint, and the production build passed.
- Dependency audit found no known vulnerabilities.
- PostgreSQL tests cover both user lock orders, two acceptances for one place,
  acceptance versus withdrawal/capacity reduction, and failed-insert rollback.
- Permission tests cover private messages/rosters, forged fields, unauthorized
  decisions/removals, owner protection, pagination, and deleted Auth identities.
- Frontend tests cover failed saves, repeated clicks, pending controls, and late
  responses after navigation or account changes.
- Local browser checks verified applying, withdrawing, resubmitting, owner review,
  acceptance, matching rosters, capacity including the owner, and leaving.
  After leaving a private project, roster access ended while accepted history remained.
