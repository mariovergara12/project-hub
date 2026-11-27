# Applications and teams

An **application** is a request to join a project. A **team** contains its owner
and current members. Application history stays saved after someone leaves a team.

## How joining works

1. Find an open project with space and choose **Apply to project**. A message is optional.
2. The owner opens **Review applications** and accepts or rejects the request.
3. Acceptance adds the applicant to the team. The project appears in **My teams**.
4. Use **My Applications** for past decisions and **My teams** for current access.

| Application status | Meaning and next step |
| --- | --- |
| `pending` | Waiting for the owner. The applicant can withdraw it. |
| `withdrawn` | Cancelled by the applicant. They can apply again if the project is open and has space. |
| `accepted` | The request was approved. Leaving or removal ends membership but keeps this decision. |
| `rejected` | The request was declined. It cannot be resubmitted. |

## Team rules

- The owner counts toward the member limit and cannot apply, leave, or be removed.
- Only the owner can accept applicants or remove another member. Members can leave themselves.
- Applying and accepting require an open project with space. Acceptance saves the decision and membership together.
- Existing members cannot apply. Each person has one application per project. Resubmitting a withdrawn request reuses that application and replaces its message.
- Leaving or removal ends team access. Repeating an old acceptance does not restore it; rejoining is not supported yet.
- Archived teams are read-only. Applicants can still withdraw pending requests.

## API notes

See the [endpoint table](backend-api-contract.md#applications-and-teams).
Application messages are limited to 2,000 trimmed characters and are visible only
to the applicant and owner. The roster exposes public user summaries, not emails
or application messages.

Application lists accept `status`, `limit`, and `cursor`; `/me/applications`
also accepts `project_id`. `/me/teams` lists current memberships and owned projects,
including private projects. Past acceptance alone never grants team access.

Repeating the same decision or withdrawal makes no change. A conflicting final
decision or full team returns `409`. On an editable team, an owner repeating removal gets
`removed: false`. Roster cursors use **user IDs**, not membership IDs.

Before releasing against an older database, apply the reviewed
[owner-membership migration](project-management.md#database-release).
