# Faculty operations

A trusted operator verifies faculty using backend database access. Users cannot
change their role through profile edits or Auth metadata. There is no public
role-change endpoint, and this command cannot change administrator accounts.

## Preview, then apply

The user must already exist in Project Hub: ask them to sign in and open their
profile. From `backend/`, run:

```sh
PROJECT_HUB_ENV_FILE=.env.supabase uv run python -m app.operators.faculty \
  --user-id USER_UUID \
  --status verified \
  --operator 'Your name or work identity' \
  --reason 'How faculty status was checked' \
  --expected-database postgres \
  --expected-project-ref YOUR_PROJECT_REF
```

This is a **dry run**. Check the account, target database/project, and proposed
change. Repeat the command with `--apply` only when the change is approved.
For local PostgreSQL, select the local environment/database and omit
`--expected-project-ref`. The command rejects mismatched targets.

| Status | Result |
| --- | --- |
| `verified` | Faculty role with verification; can create research opportunities. |
| `unverified` | Faculty role without verification; removes existing verification. |
| `student` | Student role without verification. |

`--operator` records who made the change; it does not grant access. Repeating the
current status makes no change and creates no duplicate audit record.

## Audit and rollback

Apply migration `71d9cfa35335` before using `--apply`. Each change saves its audit
record and role update together; an audit failure rolls both back. Audit records
survive account deletion and are private to trusted database operators.

To reverse a role change, run a new reviewed command with a new reason.
Do not use migration downgrade as an undo: it drops audit history without
reversing role assignments. Preserve the audit table and its backups.
