# Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution. It’s designed around a few core entities:

- **Projects**: private/public containers with membership permissions
- **Epics**: large initiatives (EP-#)
- **Sprints**: timeboxed delivery windows
- **User Stories**: backlog items (US-#)
- **Subtasks**: checklist-level work on a story (ST-#)
- **Comments**: collaboration trail on stories and issues
- **Issues**: bugs / tech debt / NCR-style tracked items (IS-#)
- **Milestones**: releases / phase gates / deadlines
- **Wiki Pages**: lightweight project documentation
- **Activity Log**: append-only audit trail of project events

## Permissions & Privacy

- **Private projects** are only visible to the owner, members, and superusers.
- Membership permissions are granular:
  - **Read**: view project, lists, and details
  - **Comment**: add comments to stories/issues
  - **Edit**: create/update work items
  - **Invite**: add members
  - **Delete**: delete work items

## Where to find it

- UI: navigate to `/project-management` in the dashboard.
- API (for integrations): `/api/v1/project-management/*` (and related endpoints).

## Role quickstarts

Use this section as guidance; your actual visibility depends on your assigned permissions.

### CEO / Executive

- Review project health: backlog size, sprint throughput, risk/issue trends.
- Use the activity log as an audit trail for key changes (scope/status/ownership).
- Focus on milestones and blockers rather than individual subtasks.

### General Manager (GM)

- Own the delivery cadence: sprints, sprint goals, and cross-team dependencies.
- Use stories/subtasks for execution; use issues for defects/NCRs/recurring problems.
- Keep milestones aligned to delivery commitments and customer dates.

### Supervisor / Team Lead

- Keep the sprint board current (stories status, subtasks closed, comments on blockers).
- Ensure issues are triaged and assigned, with due dates when needed.
- Document decisions in comments so handoffs are clear.

### Operator

- If assigned work, focus on your subtasks and add comments when blocked.
- Use story comments to capture “what happened” (facts) and tag supervisors if needed.

### Quality / Engineering

- Track defects and NCR follow-ups as issues (severity/priority/status).
- Link investigation and corrective actions in comments and wiki pages.
- Monitor milestone readiness (open/closed items).

### Maintenance

- Track repair tasks as stories/subtasks (or issues when it’s a defect trend).
- Add completion notes in comments for traceability.

### Sales / Finance / HR / Auditor / Warehouse / IT / Admin

- Use read-only access for visibility into commitments, due dates, and blockers.
- Use comments to request clarification or record approvals if your role includes it.
- Admin/IT: manage access and investigate via activity logs when needed.
