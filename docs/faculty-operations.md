# Faculty operations

Faculty status is managed by a trusted operator with backend database access.
Users cannot assign it through profile edits, tokens, or Auth metadata.
The command cannot change administrator accounts or create new accounts.

## Review a change

Use an existing application user UUID. The user must have signed in and opened
their profile at least once. From `backend/`, run:

```sh
PROJECT_HUB_ENV_FILE=.env.supabase .venv/bin/python -m app.operators.faculty \
  --user-id USER_UUID \
  --status verified \
  --operator 'Operator name or work identity' \
  --reason 'How faculty status was checked' \
  --expected-database postgres \
  --expected-project-ref YOUR_PROJECT_REF
```

This defaults to a dry run and changes nothing. After checking the user, target,
and proposed values, repeat with `--apply` to save the change and audit record.
The database name, database project, and Auth project must match the explicit
arguments. For a local database use the local environment and omit the project ref.
Connection-target query overrides are rejected.

Supported statuses:

- `verified`: faculty role with a verification timestamp.
- `unverified`: faculty role without verification; also removes existing verification.
- `student`: student role without verification.

Repeating the current status changes nothing and adds no duplicate audit entry.
The command takes its privileges from trusted database access. `--operator` is
an attribution label, not an authentication mechanism.

## Audit and release

Migration `71d9cfa35335` adds `faculty_role_changes`. Each actual change records the
user UUID, previous/new role and verification, operator, database principal,
reason, and time. Role and audit changes commit together. Failed audit writes
leave the role unchanged. Records survive account deletion.

The audit table has RLS enabled, no client policies, and no public/client grants.
It is not exposed through the application API. Database operators remain trusted
and must preserve audit records in backups.

Release after review:

1. Apply the additive audit migration to the selected shared database. It does
   not change existing accounts and remains compatible with the current API.
2. Release the updated API, including PUT support in CORS, and verify both profile
   selection endpoints before publishing the updated frontend.
3. Run faculty commands only for explicitly reviewed account changes.

For a code rollback, keep the audit table and saved selections. Downgrading this
migration drops the audit history and does not undo role assignments; export the
history before any deliberate downgrade. Reverse an assignment through a new
reviewed operator command with its own reason and audit record.

No shared migration or faculty assignment was performed during implementation.
