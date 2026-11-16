# Project management

The backend branch includes project creation, owner editing, status controls,
and My Projects. The frontend branch and main are unchanged.

## Database release

Alembic revision `9eb18a4d2620` follows `71d9cfa35335` and adds missing owner
memberships to existing projects. It creates no tables and changes no capacity
limits. It preserves existing owner memberships and joining dates.

Before applying it to the shared database, review projects that lack their
owner's membership and are already at capacity. The migration stops atomically
if any such project exists. Decide whether to adjust capacity or membership,
then retry. Do not silently change these records. The migration briefly locks
users, projects, and memberships, so schedule it with application writes paused
and use the usual database backup and release process.

Downgrade preserves memberships because they cannot safely be distinguished from
legitimate application data. Rolling back API code does not undo owner counts.
The demo seed also creates owner memberships and preserves edited project fields
and requirements, including intentionally empty selections.

## Verification

Use a separate local database for migrations and browser checks. Test creation
with user A, draft privacy with user B, publishing, owner-only editing, skills
and interests, capacity including the owner, and status changes through archive.
Backend tests also exercise invalid fields, failed-write rollback, faculty
permissions, owner-list pagination, and the legacy-data migration guard.

The shared database migration and production release require separate review.
