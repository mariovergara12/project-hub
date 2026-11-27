# Project management

Use **My projects** for projects you own and **My teams** for projects you own or
have joined. Only the owner can edit project details or change project status.

## Project lifecycle

| Status | What it means |
| --- | --- |
| `draft` | Private draft. Publish it to start recruiting. |
| `open` | Visible to signed-in users and accepting applications when space is available. |
| `in_progress` | Work has started; visible only to the owner and current members. |
| `completed` | Finished; visible only to the owner and current members. Milestones are read-only. |
| `archived` | Project details, team membership, and milestones are read-only. |

Statuses move forward: `draft → open → in_progress → completed`.
Any non-archived project can be archived. Neither completing nor archiving can
be undone through the API. Sending the current status again makes no change.

## Create and edit

Create a project with a title and description. It starts as a draft, and its
owner becomes its first member. Skills, interests, hours, experience, and capacity
are optional. Capacity includes the owner and cannot be reduced below the current
member count.

Creating, editing, or publishing research opportunities requires verified faculty.
An owner who loses verification can convert the project to a student project or
archive it. See [faculty operations](faculty-operations.md).

For PATCH requests, omit a field to keep it, use `[]` to clear skills/interests,
and use `null` to clear optional numeric values. Use the dedicated status endpoint
to change status. See the [API contract](backend-api-contract.md#projects).

## Milestones

Open **Milestones** from project details (owner) or the team page (members).
Owners and current members can add, edit, change status, and delete milestones.
Each milestone has a title, optional description/due date, and a status:
`todo`, `in_progress`, or `completed`. Active projects allow reopening milestones.

Progress counts every milestone, even when the list is filtered or paginated.
Completed and archived projects allow milestone reads but no changes.
Leaving or removal ends milestone access, even if application history says accepted.

## Database release

Review and apply these migrations in order before releasing the updated API:

| Revision | Purpose |
| --- | --- |
| `71d9cfa35335` | Add private faculty audit records. |
| `9eb18a4d2620` | Add missing owner memberships to existing projects. |

The owner backfill preserves existing memberships and joining dates. It stops
without changes if adding an owner would exceed capacity; review those projects
before retrying. It does not raise capacity or remove members automatically.
Pause application writes and use your normal backup process when applying it.
Downgrade keeps the added memberships; rolling back code does not remove them.
Milestones use the existing table and need no additional migration.

Test migrations on a separate local database first. See
[database setup](database-setup.md) for connection and test commands.
