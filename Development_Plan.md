# Sensei OS — Development Master Plan

**End of Development Plan**


### 1.1. Technology Stack Selection & Setup
- [ ] **Frontend**: Initialize React/Next.js project (Mobile-first responsive design).
- [ ] **Backend**: Initialize API framework (Node.js/NestJS or Python/FastAPI).
- [ ] **Database**: Provision PostgreSQL database.
- [ ] **File Storage**: Setup S3-compatible storage for attachments (Drawings, Specs).
- [ ] **DevOps**: Configure Docker containers and CI/CD pipelines (GitHub Actions/GitLab CI).

### 1.2. Database Schema Design (Section 11)
- [ ] **Core Entities**: Create tables for `User`, `Account`, `Contact`, `Opportunity`.
- [ ] **RFQ & Quote**: Create tables for `RFQ`, `RFQ_Question`, `Qualification`, `Quote`, `Quote_Version`, `Supplier_Quote`.
- [ ] **Operational**: Create tables for `CTQ`, `Risk`, `Obeya_Item`, `A3`, `Task`.
- [ ] **Learning**: Create tables for `Learning_Unit`, `User_Learning_Progress`.
- [ ] **Phase 3 Placeholders**: Define schemas for `Work_Order`, `Station`, `Standard_Work`, `Andon_Event`, `NC_Record`.
- [ ] **Audit Fields**: Ensure all tables have `created_at`, `updated_at`, `created_by`, `owner`, `status`.

### 1.3. Security & Authentication (Section 13.1)
- [ ] Implement Role-Based Access Control (RBAC) (Roles: GM, Sales Engineer, Estimator, Quality, Supply Chain, Ops, Exec).
- [ ] Implement JWT/Session authentication.
- [ ] Enforce 2FA (TOTP) for Admin and GM roles.
- [ ] Configure encryption at rest (Database) and in transit (TLS).
- [ ] Implement field-level permissions for sensitive financial data (Margin, Costing).

### 1.4. Offline & Mobile Capabilities (Enhancement)
- [ ] **PWA Configuration**: Configure Service Workers for offline caching of critical data (Today screen, active RFQs).
- [ ] **Sync Engine**: Implement "Optimistic UI" updates with background sync when connection is restored.
- [ ] **Mobile Features**: Integrate camera access for scanning documents/QR codes directly into RFQ/Andon forms.

### 1.5. Environments, Configuration, and Migrations (Enhancement)
- [ ] **Environments**: Define `dev` / `staging` / `prod` environment strategy with isolated databases and storage buckets.
- [ ] **Configuration**: Centralize environment variables and secrets (no secrets in repo), plus config validation on startup.
- [ ] **DB Migrations**: Add repeatable migrations + seed data for roles, default stages, default thresholds, and templates.
- [ ] **Feature Flags**: Add feature-flag mechanism for phased rollout (Phase 2/3 modules disabled by default).

### 1.6. Observability & Audit Integrity (Enhancement)
- [ ] **Structured Logging**: Implement request/actor/object logging for all writes (especially approvals/overrides).
- [ ] **Metrics**: Track latency for Today/Search/PDF generation and background job health.
- [ ] **Error Tracking**: Capture server/client exceptions with correlation IDs.
- [ ] **Audit Log Hardening**: Implement append-only audit log semantics (tamper-evident hashes) for critical actions.

### 1.7. Background Jobs & Schedulers (Enhancement)
- [ ] **Job System**: Add a queue/scheduler for stale detection, reminders, learning prompts, and recurring exports.
- [ ] **Idempotency**: Ensure jobs are idempotent and retry-safe (especially PDF generation and email drafts).
- [ ] **Time Zones**: Run cadence jobs in Morocco time for GM routines.

---

## 2. Phase 1: Core Data & CRM (Foundation)

### 2.1. CRM & Pipeline Module (Section 8.3)
- [ ] **Pipeline Management**: Implement configurable pipeline stages.
- [ ] **Opportunity Tracking**:
    - [ ] Create CRUD for Opportunities.
    - [ ] Enforce "Next Step" and "Due Date" fields for every opportunity.
    - [ ] Implement "Stale Detection" job (Flag opportunities with no activity for X days).
- [ ] **Activity Logging**: Implement logging for Calls, Emails, Meetings.
- [ ] **Views**: Build List view and Kanban board view (by stage, value, probability).
- [ ] **Smart Ingestion (Enhancement)**: Implement OCR/AI parsing for incoming RFQ emails/PDFs to auto-create opportunities.

### 2.2. Master Data Management
- [ ] **Accounts & Contacts**: Implement management for Customers and Suppliers.
- [ ] **Supplier Database**: Include capabilities and responsiveness scores.
- [ ] **Supplier Portal Lite (Enhancement)**: Create a secure, tokenized link for suppliers to upload quotes directly, bypassing email chains.

### 2.3. Tasks, Notifications, and Cadence Engine (Enhancement)
- [ ] **Task System (Core)**: Implement `Task` creation, assignment, due dates, status, and linkage to all objects.
- [ ] **Notification Rules**: Generate notifications for overdue tasks, stalled opportunities, missing RFQ inputs, and approval requests.
- [ ] **Digest Exports**: Generate a daily “Today snapshot” and weekly Obeya snapshot export (PDF) for HQ sharing.
- [ ] **Escalation**: Add escalation policy for aging approvals and high-severity risks.

### 2.4. Global Search & Retrieval (Enhancement)
- [ ] **Full-Text Search**: Implement search across Accounts, RFQs, Quotes, CTQs, A3s, and Tasks.
- [ ] **Saved Views**: Allow saving common filters (e.g., “Quotes due this week”, “Red items”, “Stale opps”).
- [ ] **Fast Navigation**: Add quick-open search for rapid GM use on mobile.

### 2.5. RBAC Permissions Matrix (Enhancement)
- [ ] **Role Definitions**: Define capabilities per role (view/create/update/approve/export/admin).
- [ ] **Approval Permissions**: Explicitly define who can approve: qualification overrides, quote releases, margin exceptions, template edits.
- [ ] **Object-Level Rules**: Restrict access by account/customer where needed (e.g., supplier quotes visible to estimator/GM only).
- [ ] **Field-Level Rules**: Formalize what is considered “sensitive financial data” and enforce read/write restrictions.
- [ ] **Audit Visibility**: Decide which roles can view audit trails and approval rationales.

---

## 3. Phase 1: RFQ & Qualification Engine

### 3.1. RFQ Desk (Intake) (Section 8.4)
- [ ] **RFQ Object**: Implement fields: Customer, Product Family, Specs, BOM, Volume, Ramp Plan, Target Price, Incoterms, Location, Compliance, Samples, Testing, Packaging.
- [ ] **Completeness Logic**:
    - [ ] Implement algorithm to calculate Completeness Score (0-100).
    - [ ] Block transition to "Qualification" if score < threshold (unless GM override).
- [ ] **Missing Info Workflow**:
    - [ ] Auto-generate "Missing Info Request" email text based on empty fields.
    - [ ] Auto-create tasks for missing items.
- [ ] **Technical Q&A**: Implement Q&A log with Owner and Due Date.

### 3.2. Qualification Engine (Section 8.5)
- [ ] **Scoring Dimensions**: Implement input forms for Capability, Strategic, Risk, Commercial, and Operational fit.
- [ ] **Decision Logic**:
    - [ ] Implement outcomes: No Quote / Quote / Quote with Conditions.
    - [ ] Enforce mandatory rationale for decisions.
    - [ ] Implement GM Approval workflow for Overrides.
- [ ] **Conditions Library**:
    - [ ] Create template library for: MOQ, Lead Time, Price Validity, Payment Terms, NRE, Yield, etc.
    - [ ] Implement "Hard Stop" rules (e.g., missing compliance).
- [ ] **Reporting**: Generate 1-page Qualification PDF.

### 3.3. Risk Register (Phase 1) (Enhancement)
- [ ] **Risk Object UX**: Create risk capture/edit UI with category, severity, owner, mitigation, due date.
- [ ] **Risk Scoring**: Implement a simple scoring model (severity × likelihood) and use it to prioritize Today/Obeya.
- [ ] **Linkage**: Link risks to Opportunities/RFQs/Quotes and propagate “Top risks” onto Today.

### 3.4. Attachments, Versioning, and Traceability (Enhancement)
- [ ] **Attachments**: Implement versioned attachments on RFQs/Quotes/CTQs/A3s with metadata (revision, uploader, timestamp).
- [ ] **Revision Control**: Enforce spec revision tracking on RFQ and block qualification/quote release if unclear without override.
- [ ] **Audit Trail UI**: Provide an object-level timeline (who changed what, when) beyond approvals.

### 3.5. Workflow State Machines & Gates (Enhancement)
- [ ] **Opportunity State Model**: Define allowed stage transitions and required fields for each transition.
- [ ] **RFQ State Model**: `Draft` → `Intake` → `Waiting on Customer` → `Complete` → `Qualification` (with completeness threshold and override).
- [ ] **Qualification State Model**: `Not Started` → `In Progress` → `Decision Proposed` → `Approved` (or `Rejected`) with override path.
- [ ] **Task State Model**: `Open` → `In Progress` → `Blocked` → `Done` (with blocked reason required).
- [ ] **Gate Enforcement**: Centralize gate rules so UI + API always enforce the same constraints.

---

## 4. Phase 1: Quoting & Customer Onboarding

### 4.1. Quote Builder (Section 8.6)
- [ ] **Costing Engine**:
    - [ ] Build inputs for: BOM cost, Labor, Overhead, Test, Scrap/Yield, Packaging, Logistics.
    - [ ] Implement "Virtual Routing" for routing assumptions.
- [ ] **Quote Structure**:
    - [ ] Header: Customer, Reference, Revision, Validity.
    - [ ] Commercials: Price breaks, MOQ, Lead time, Incoterms.
    - [ ] **Assumptions Log**: Mandatory section for every quote.
- [ ] **Supplier Quote Tracking**: Track Requested/Received/Validity status.
- [ ] **Versioning**: Implement immutable version control (Revisions create new IDs).
- [ ] **Collaboration (Enhancement)**: Enable inline comments and "mention" (@user) functionality on line items for team collaboration.
- [ ] **Simulation Mode (Enhancement)**: Add "What-If" scenario planning (e.g., "If material cost +10%, margin = ?") without altering the draft.

### 4.2. Approval Workflow
- [ ] **Rules Engine**:
    - [ ] Trigger Finance/GM approval if Margin < Threshold.
    - [ ] Trigger Ops approval for Lead Time commitments.
    - [ ] Trigger GM approval for Unusual Terms.
- [ ] **Audit**: Log all approvals with user and timestamp.
- [ ] **Visual Timeline (Enhancement)**: Implement a graphical timeline view of the Quote lifecycle showing all edits, approvals, and status changes.

### 4.3. Output Generation
- [ ] **PDF Generator**: Implement PDF generation matching brand template.

### 4.4.1. Export and Document Controls (Enhancement)
- [ ] **Export Types**: Quote PDF, Qualification report PDF, Today snapshot PDF, Obeya snapshot PDF, Week in Review PDF.
- [ ] **Branding Controls**: Centralize header/footer, revision watermarking, and per-customer legal boilerplate.
- [ ] **Language Controls**: Support English/French document generation (and future Arabic readiness).
- [ ] **Immutability**: Ensure exported PDFs are attached to the specific immutable version (quote version, qualification decision version).

### 4.4. Customer Onboarding (Section 8.7)
- [ ] **CTQ Capture**:
    - [ ] Create CTQ Object: Requirement, Measurement, Criteria, Check Stage, Evidence.
    - [ ] Gate "Ready for NPI" status on CTQ completion (or waiver).

### 4.5. Templates, Libraries, and Guardrails (Enhancement)
- [ ] **Template Center**: Manage Conditions library text, PDF brand templates, and default assumptions per product family.
- [ ] **Pricing/Margin Policy Pack**: Store margin floors by segment, exception reasons, and required evidence fields.
- [ ] **Quote Quality Checks**: Add pre-release validation (missing assumptions, missing supplier validity, missing CTQ links).

---

## 5. Phase 1: Management & Learning Systems

### 5.1. Manager GPS ("Today" Screen) (Section 8.2)
- [ ] **Dashboard Logic**:
    - [ ] **Top 3 Priorities**: Forced selection UI.
    - [ ] **Top Risks**: Display Delivery/Quality/Cash/Reputation risks.
    - [ ] **Commitments**: Aggregate due quotes, calls, follow-ups.
    - [ ] **Abnormalities**: Query late quotes, stalled RFQs, missing CTQs.
- [ ] **Micro-Drill**: Display 2-3 recall questions daily.
- [ ] **LSW Checklist**: Implement interactive Daily/Weekly/Monthly checklist.
- [ ] **Performance**: Ensure load time < 2 seconds.

### 5.2. Obeya (Section 8.8)
- [ ] **Digital Board**: Implement SQDCP (Safety, Quality, Delivery, Cost, People) view.
- [ ] **Exception Logic**: Only show trends and red items.
- [ ] **Countermeasures**: Link red items to Owners and Due Dates.

### 5.3. Problem Solving (A3-lite) (Section 8.9)
- [ ] **A3 Builder**:
    - [ ] Sections: Problem, Current, Target, Root Cause (5-Why), Countermeasures, Plan, Results, Reflection.
    - [ ] **Triggers**: Auto-create A3 from recurring errors (e.g., quote error).
- [ ] **Closure Logic**: Enforce "Reflection" and "Standard Update" before closing.

### 5.4. Learning Engine (Section 8.10)
- [ ] **Content Management**: Support Micro-lessons, Retrieval prompts, Guided templates.
- [ ] **Spaced Repetition Algorithm**:
    - [ ] Scheduler: Assign prompts based on role + recent actions.
    - [ ] Logic: Incorrect = sooner repetition; Correct = later.
- [ ] **Contextual Delivery**: Link lessons to specific objects (e.g., show RFQ lesson on RFQ screen).
- [ ] **Sensei Nudges (Enhancement)**: Implement real-time, context-aware tips inside forms (e.g., "Low margin detected. Have you checked scrap rates?").

### 5.5. Leadership Standard Work Automation (Enhancement)
- [ ] **LSW Scheduling**: Auto-generate recurring LSW items (daily/weekly/monthly) with reminders and completion evidence.
- [ ] **Meeting Notes Capture**: Standard template for tier/obeya notes that produces Tasks, Risks, and A3 triggers.
- [ ] **HQ Share Pack**: One-click “Week in Review” export (Today + Obeya + top risks + open A3s).

### 5.6. Analytics, KPIs, and Decision Support (Enhancement)
- [ ] **KPI Definitions (Phase 1)**: Implement the Phase 1 KPI set (RFQ completeness, qualification discipline, quote cycle time, revision rate, margin protection, win/bad-win, cadence adherence, knowledge capture).
- [ ] **Metric Sources**: Define exactly which events/fields power each KPI (e.g., quote cycle time = RFQ created_at → quote released_at).
- [ ] **Trends vs Noise**: Ensure Obeya and KPI views prioritize trends/exceptions, not raw tables.
- [ ] **Segment Views**: Support slicing by customer segment/product family/owner while preserving “exceptions-first” UX.

### 5.7. Notifications Matrix (Enhancement)
- [ ] **Triggers**: Enumerate triggers (overdue follow-ups, stalled RFQs, missing CTQs, low-margin quote, aging approvals, recurring abnormalities).
- [ ] **Recipients**: Define recipients by role and object ownership (owner, GM, approver, exec sponsor).
- [ ] **Channels**: In-app notifications first; add email later as integration (copy-ready minimum remains acceptable).
- [ ] **Snooze/Acknowledge**: Add acknowledge and snooze to prevent notification fatigue.

---

## 6. Phase 2: NPI & Industrialization (Future)

### 6.1. NPI Stage Gates (Section 9.1)
- [ ] **Workflow**: Implement stages: Intake → DFM → Prototype → Pilot → SOP.
- [ ] **Gating Logic**: Block transition without required artifacts (CTQs, Process Plan, Supplier Readiness).

### 6.2. Readiness Tools
- [ ] **Checklists**: Implement Supplier Readiness and PPAP-lite checklists.
- [ ] **Risk Register**: Expand Risk object for NPI specific risks.

---

## 7. Phase 3: Production & TPS Execution (Future)

Phase 3 implements the Toyota Production System (TPS) principles for shop floor execution, enabling
real-time production control, quality management, standardized work, and continuous improvement.

### 7.1. Production Entities & Core Schema

#### 7.1.1. Work Center & Station Management
- [ ] **WorkCenter Model**: Implement production work center entity.
    - [ ] Fields: `id`, `name`, `code`, `description`, `location`, `capacity_units`, `efficiency_target`, `status`.
    - [ ] Relationships: belongs to `Account`, has many `Station`, has many `WorkOrder`.
    - [ ] Status Enum: `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `DECOMMISSIONED`.
- [ ] **Station Model**: Implement individual work stations within work centers.
    - [ ] Fields: `id`, `work_center_id`, `name`, `code`, `station_type`, `takt_time_seconds`, `cycle_time_seconds`, `status`.
    - [ ] Station Type Enum: `ASSEMBLY`, `MACHINING`, `INSPECTION`, `PACKAGING`, `TESTING`, `REWORK`.
    - [ ] Relationships: belongs to `WorkCenter`, has many `StandardWork`, has many `AndonEvent`.
    - [ ] Constraints: Unique `code` within work center, takt_time > 0, cycle_time > 0.

#### 7.1.2. Product & Routing
- [ ] **Product Model**: Implement product master data.
    - [ ] Fields: `id`, `name`, `part_number`, `revision`, `description`, `product_family`, `unit_of_measure`, `status`.
    - [ ] Product Status Enum: `ACTIVE`, `OBSOLETE`, `PROTOTYPE`, `DISCONTINUED`.
    - [ ] Relationships: has many `BOMItem`, has many `Routing`, has many `StandardWork`.
    - [ ] Constraints: Unique `part_number` + `revision` combination.
- [ ] **BOMItem Model**: Bill of Materials line items.
    - [ ] Fields: `id`, `product_id`, `component_part_number`, `quantity`, `unit_of_measure`, `position`, `is_critical`.
    - [ ] Relationships: belongs to `Product`.
- [ ] **Routing Model**: Production routing steps.
    - [ ] Fields: `id`, `product_id`, `sequence`, `station_id`, `operation_name`, `standard_time_seconds`, `setup_time_seconds`.
    - [ ] Relationships: belongs to `Product`, references `Station`.
    - [ ] Constraints: Unique sequence per product.

#### 7.1.3. Work Order Management
- [ ] **WorkOrder Model**: Production work order entity.
    - [ ] Fields: `id`, `work_order_number`, `product_id`, `quantity_ordered`, `quantity_completed`, `quantity_scrapped`, `priority`, `status`, `scheduled_start`, `scheduled_end`, `actual_start`, `actual_end`, `current_station_id`.
    - [ ] Work Order Status Enum: `DRAFT`, `RELEASED`, `IN_PROGRESS`, `ON_HOLD`, `COMPLETED`, `CANCELLED`.
    - [ ] Priority Enum: `LOW`, `NORMAL`, `HIGH`, `URGENT`, `CRITICAL`.
    - [ ] Relationships: references `Product`, references `Station`, has many `WorkOrderOperation`.
    - [ ] Constraints: `work_order_number` unique, quantity_ordered > 0.
- [ ] **WorkOrderOperation Model**: Individual operations within a work order.
    - [ ] Fields: `id`, `work_order_id`, `routing_id`, `sequence`, `station_id`, `status`, `quantity_completed`, `quantity_scrapped`, `started_at`, `completed_at`, `operator_id`.
    - [ ] Operation Status Enum: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `SKIPPED`, `BLOCKED`.
    - [ ] Relationships: belongs to `WorkOrder`, references `Routing`, references `Station`, references `User`.

### 7.2. Standard Work & Training (Section 10.1, 10.2)

#### 7.2.1. Standard Work Document Management
- [ ] **StandardWork Model**: Versioned standard work documents.
    - [ ] Fields: `id`, `document_number`, `title`, `description`, `product_id`, `station_id`, `version`, `status`, `content_json`, `effective_date`, `expiration_date`, `approved_by`, `approved_at`.
    - [ ] Document Status Enum: `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `SUPERSEDED`, `OBSOLETE`.
    - [ ] Content JSON Schema: Array of steps with `sequence`, `instruction`, `image_attachment_id`, `estimated_time_seconds`, `safety_notes`, `quality_checkpoints`.
    - [ ] Relationships: references `Product`, references `Station`, references `User` (approved_by), has many `StandardWorkVersion`.
    - [ ] Constraints: Unique `document_number` + `version`.
- [ ] **StandardWorkVersion Model**: Immutable version history.
    - [ ] Fields: `id`, `standard_work_id`, `version`, `content_json`, `change_summary`, `created_by`, `created_at`.
    - [ ] Relationships: belongs to `StandardWork`, references `User`.
    - [ ] Constraints: Version numbers monotonically increasing.
- [ ] **Standard Work Approval Workflow**:
    - [ ] Draft → Pending Approval (on submit) → Approved (on approval) → Superseded (when new version approved).
    - [ ] Approval requires role: `QUALITY_MANAGER`, `PRODUCTION_MANAGER`, or `GM`.
    - [ ] All approvals logged to `AuditLog` with rationale.
- [ ] **Standard Work Change Control**:
    - [ ] Changes create new version, previous becomes `SUPERSEDED`.
    - [ ] Mandatory fields: `change_summary` (min 20 chars), `effective_date`.
    - [ ] Emergency changes allowed with GM override + rationale.

#### 7.2.2. Skills & Competency Framework
- [ ] **Skill Model**: Define skills taxonomy.
    - [ ] Fields: `id`, `name`, `code`, `description`, `skill_category`, `proficiency_levels`, `is_safety_critical`, `recertification_interval_days`.
    - [ ] Skill Category Enum: `TECHNICAL`, `QUALITY`, `SAFETY`, `LEADERSHIP`, `EQUIPMENT`, `PROCESS`.
    - [ ] Proficiency Levels: JSON array defining levels (e.g., `["Awareness", "Basic", "Proficient", "Expert", "Trainer"]`).
    - [ ] Constraints: Unique `code`, recertification_interval >= 0.
- [ ] **SkillRequirement Model**: Link skills to stations/products.
    - [ ] Fields: `id`, `skill_id`, `station_id`, `product_id`, `minimum_proficiency_level`, `is_mandatory`.
    - [ ] Relationships: references `Skill`, optionally references `Station`, optionally references `Product`.
    - [ ] Constraints: At least one of `station_id` or `product_id` must be set.

#### 7.2.3. Training Matrix & Certification
- [ ] **Training Model**: Training events/courses.
    - [ ] Fields: `id`, `skill_id`, `name`, `description`, `training_type`, `duration_hours`, `max_participants`, `trainer_id`, `scheduled_date`, `location`, `status`.
    - [ ] Training Type Enum: `CLASSROOM`, `ON_THE_JOB`, `E_LEARNING`, `CERTIFICATION_EXAM`, `RECERTIFICATION`.
    - [ ] Training Status Enum: `SCHEDULED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
    - [ ] Relationships: references `Skill`, references `User` (trainer), has many `TrainingParticipant`.
- [ ] **TrainingParticipant Model**: User enrollment and completion.
    - [ ] Fields: `id`, `training_id`, `user_id`, `enrollment_status`, `attendance_status`, `score`, `passed`, `completed_at`, `certificate_number`.
    - [ ] Enrollment Status Enum: `ENROLLED`, `WAITLISTED`, `CANCELLED`, `NO_SHOW`.
    - [ ] Attendance Status Enum: `PENDING`, `ATTENDED`, `PARTIAL`, `ABSENT`.
    - [ ] Relationships: belongs to `Training`, references `User`.
    - [ ] Constraints: Unique `user_id` + `training_id`.
- [ ] **UserSkill Model**: User competency and certification records.
    - [ ] Fields: `id`, `user_id`, `skill_id`, `proficiency_level`, `certification_status`, `certified_date`, `expiration_date`, `certified_by`, `certificate_number`, `notes`.
    - [ ] Certification Status Enum: `NOT_CERTIFIED`, `IN_TRAINING`, `CERTIFIED`, `EXPIRED`, `SUSPENDED`.
    - [ ] Relationships: references `User`, references `Skill`, references `User` (certified_by).
    - [ ] Constraints: Unique `user_id` + `skill_id`.
- [ ] **Training Matrix View Logic**:
    - [ ] Matrix display: Users (rows) × Skills (columns) with proficiency/status indicators.
    - [ ] Gap analysis: Identify users missing required skills for their assigned stations.
    - [ ] Expiration alerts: Flag certifications expiring within 30/60/90 days.
    - [ ] Auto-generate recertification tasks when approaching expiration.

### 7.3. Shop Floor Control (Section 10.3, 10.5)

#### 7.3.1. Andon System
- [ ] **AndonEvent Model**: Real-time production issue logging.
    - [ ] Fields: `id`, `event_number`, `station_id`, `product_id`, `work_order_id`, `andon_type`, `severity`, `symptom`, `description`, `photo_attachment_id`, `status`, `reported_by`, `reported_at`, `acknowledged_by`, `acknowledged_at`, `resolved_by`, `resolved_at`, `resolution_notes`, `escalated_to_a3_id`.
    - [ ] Andon Type Enum: `QUALITY`, `EQUIPMENT`, `MATERIAL`, `SAFETY`, `PROCESS`, `INFORMATION`.
    - [ ] Severity Enum: `YELLOW` (warning), `RED` (stop), `BLUE` (material call).
    - [ ] Andon Status Enum: `OPEN`, `ACKNOWLEDGED`, `IN_PROGRESS`, `RESOLVED`, `ESCALATED`.
    - [ ] Relationships: references `Station`, references `Product`, references `WorkOrder`, references `User` (multiple), optionally references `A3`, has many `Attachment`.
    - [ ] Constraints: `event_number` unique, auto-generated sequence.
- [ ] **Stop-Call-Wait Workflow Logic**:
    - [ ] **STOP**: When Andon triggered, work order operations at station automatically marked `BLOCKED`.
    - [ ] **CALL**: Notification sent to station supervisor and quality team based on Andon type.
    - [ ] **WAIT**: Timer starts on acknowledgement; escalation rules if not acknowledged within SLA.
    - [ ] SLA Configuration: `yellow_ack_minutes`, `red_ack_minutes`, `resolution_target_minutes` per station.
- [ ] **AndonEscalation Model**: Escalation rules and history.
    - [ ] Fields: `id`, `andon_event_id`, `escalation_level`, `escalated_to_user_id`, `escalated_at`, `response_status`, `responded_at`.
    - [ ] Escalation Level: 1 (supervisor), 2 (manager), 3 (GM).
    - [ ] Response Status Enum: `PENDING`, `ACKNOWLEDGED`, `DELEGATED`, `NO_RESPONSE`.
- [ ] **A3 Auto-Escalation Logic**:
    - [ ] Track recurrence: Same `station_id` + `andon_type` + `symptom` pattern.
    - [ ] Threshold: 3 occurrences within 7 days triggers A3 creation.
    - [ ] A3 auto-populated with: problem statement from symptom, affected station/product, occurrence dates.
    - [ ] Link all related Andon events to A3.
- [ ] **Andon Dashboard (Real-Time)**:
    - [ ] Visual board showing all stations with current status (green/yellow/red).
    - [ ] Active Andon list with elapsed time counters.
    - [ ] Historical metrics: MTTR (Mean Time To Resolution), Andon frequency by type/station.

#### 7.3.2. Kanban System
- [ ] **KanbanBoard Model**: Digital Kanban board configuration.
    - [ ] Fields: `id`, `name`, `work_center_id`, `board_type`, `wip_limit_global`, `columns_config_json`.
    - [ ] Board Type Enum: `PRODUCTION`, `MATERIAL`, `ENGINEERING`, `MAINTENANCE`.
    - [ ] Columns Config: JSON array of columns with `name`, `wip_limit`, `color`, `order`.
    - [ ] Relationships: references `WorkCenter`, has many `KanbanCard`.
- [ ] **KanbanCard Model**: Digital Kanban cards.
    - [ ] Fields: `id`, `board_id`, `card_number`, `card_type`, `title`, `description`, `priority`, `column_name`, `position`, `work_order_id`, `product_id`, `quantity`, `due_date`, `assigned_to`, `status`, `blocked_reason`, `cycle_started_at`, `cycle_completed_at`.
    - [ ] Card Type Enum: `WORK_ORDER`, `MATERIAL_REPLENISHMENT`, `ENGINEERING_REQUEST`, `MAINTENANCE_REQUEST`.
    - [ ] Card Status Enum: `ACTIVE`, `BLOCKED`, `COMPLETED`, `CANCELLED`.
    - [ ] Relationships: belongs to `KanbanBoard`, optionally references `WorkOrder`, references `Product`, references `User`.
    - [ ] Constraints: `card_number` unique per board.
- [ ] **WIP Limit Enforcement Logic**:
    - [ ] Column-level WIP limits: Block card entry if column at limit.
    - [ ] Global board WIP limit: Total active cards cannot exceed global limit.
    - [ ] Override mechanism: GM can override with rationale (logged to audit).
    - [ ] Visual indicators: Yellow when at 80% capacity, Red when at limit.
- [ ] **Pull System Signals**:
    - [ ] Replenishment trigger: When downstream column falls below threshold, signal upstream.
    - [ ] Material Kanban: Auto-create material replenishment card when inventory below reorder point.
    - [ ] Card aging: Highlight cards exceeding expected cycle time.
- [ ] **Kanban Metrics**:
    - [ ] Lead Time: Card created → Card completed.
    - [ ] Cycle Time: Card started (entered first work column) → Card completed.
    - [ ] Throughput: Cards completed per day/week.
    - [ ] WIP aging: Cards in progress beyond target cycle time.

#### 7.3.3. Production Cell Management
- [ ] **ProductionCell Model**: Logical grouping of stations.
    - [ ] Fields: `id`, `name`, `work_center_id`, `cell_type`, `takt_time_seconds`, `target_output_per_shift`, `current_output`, `efficiency_percentage`, `status`.
    - [ ] Cell Type Enum: `U_CELL`, `LINE`, `JOB_SHOP`, `BATCH`.
    - [ ] Relationships: references `WorkCenter`, has many `Station`.
- [ ] **CellPerformance Model**: Shift-level performance tracking.
    - [ ] Fields: `id`, `cell_id`, `shift_date`, `shift_number`, `planned_output`, `actual_output`, `downtime_minutes`, `efficiency_percentage`, `oee_percentage`, `notes`.
    - [ ] OEE Calculation: Availability × Performance × Quality.
    - [ ] Relationships: belongs to `ProductionCell`.

### 7.4. Quality Management (Section 10.4)

#### 7.4.1. Non-Conformance (NC) Recording
- [ ] **NonConformance Model**: Non-conformance record.
    - [ ] Fields: `id`, `nc_number`, `nc_type`, `source`, `severity`, `product_id`, `work_order_id`, `station_id`, `quantity_affected`, `description`, `root_cause_category`, `detected_by`, `detected_at`, `status`, `disposition`, `disposition_by`, `disposition_at`, `disposition_notes`, `cost_impact`, `customer_notified`, `customer_notification_date`.
    - [ ] NC Type Enum: `MATERIAL`, `PROCESS`, `PRODUCT`, `DOCUMENTATION`, `SUPPLIER`, `CUSTOMER_RETURN`.
    - [ ] Source Enum: `INCOMING_INSPECTION`, `IN_PROCESS`, `FINAL_INSPECTION`, `CUSTOMER_COMPLAINT`, `AUDIT`.
    - [ ] Severity Enum: `MINOR`, `MAJOR`, `CRITICAL`.
    - [ ] NC Status Enum: `OPEN`, `UNDER_INVESTIGATION`, `PENDING_DISPOSITION`, `DISPOSITIONED`, `CLOSED`, `ESCALATED_TO_CAPA`.
    - [ ] Disposition Enum: `USE_AS_IS`, `REWORK`, `REPAIR`, `SCRAP`, `RETURN_TO_SUPPLIER`, `CONCESSION`.
    - [ ] Root Cause Category Enum: `HUMAN_ERROR`, `EQUIPMENT`, `MATERIAL`, `METHOD`, `ENVIRONMENT`, `MEASUREMENT`.
    - [ ] Relationships: references `Product`, references `WorkOrder`, references `Station`, references `User` (multiple), has many `Attachment`, optionally links to `CAPA`.
    - [ ] Constraints: `nc_number` unique, auto-generated.
- [ ] **NC Disposition Workflow**:
    - [ ] Open → Under Investigation (assigned to quality engineer).
    - [ ] Under Investigation → Pending Disposition (root cause identified).
    - [ ] Pending Disposition → Dispositioned (disposition decision made).
    - [ ] Dispositioned → Closed (corrective action completed) OR → Escalated to CAPA.
    - [ ] Disposition authority: Minor (Quality Inspector), Major (Quality Manager), Critical (GM approval required).
    - [ ] All status changes logged with rationale.
- [ ] **NC Containment Actions**:
    - [ ] Immediate containment: Sort, segregate, quarantine affected material.
    - [ ] Auto-generate containment tasks on NC creation for CRITICAL severity.
    - [ ] Track containment status and evidence.

#### 7.4.2. Corrective and Preventive Action (CAPA)
- [ ] **CAPA Model**: CAPA record linked to A3 problem solving.
    - [ ] Fields: `id`, `capa_number`, `capa_type`, `source_nc_id`, `source_type`, `title`, `description`, `priority`, `status`, `owner_id`, `due_date`, `root_cause_analysis`, `containment_actions`, `corrective_actions`, `preventive_actions`, `verification_method`, `verification_status`, `verified_by`, `verified_at`, `effectiveness_check_date`, `effectiveness_status`, `closed_by`, `closed_at`, `linked_a3_id`, `linked_standard_work_id`.
    - [ ] CAPA Type Enum: `CORRECTIVE`, `PREVENTIVE`, `BOTH`.
    - [ ] Source Type Enum: `NON_CONFORMANCE`, `CUSTOMER_COMPLAINT`, `AUDIT_FINDING`, `ANDON_RECURRENCE`, `MANAGEMENT_REVIEW`.
    - [ ] CAPA Status Enum: `OPEN`, `INVESTIGATING`, `IMPLEMENTING`, `VERIFYING`, `EFFECTIVE`, `CLOSED`, `INEFFECTIVE`.
    - [ ] CAPA Priority Enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
    - [ ] Verification Status Enum: `PENDING`, `PASSED`, `FAILED`, `PARTIAL`.
    - [ ] Effectiveness Status Enum: `PENDING`, `EFFECTIVE`, `PARTIALLY_EFFECTIVE`, `INEFFECTIVE`.
    - [ ] Relationships: optionally references `NonConformance`, references `User` (owner), optionally references `A3`, optionally references `StandardWork`, has many `CAPAAction`.
    - [ ] Constraints: `capa_number` unique, auto-generated.
- [ ] **CAPAAction Model**: Individual CAPA action items.
    - [ ] Fields: `id`, `capa_id`, `action_type`, `description`, `owner_id`, `due_date`, `status`, `completion_evidence`, `completed_at`, `verified`.
    - [ ] Action Type Enum: `CONTAINMENT`, `CORRECTIVE`, `PREVENTIVE`, `VERIFICATION`.
    - [ ] Action Status Enum: `OPEN`, `IN_PROGRESS`, `COMPLETED`, `OVERDUE`, `CANCELLED`.
    - [ ] Relationships: belongs to `CAPA`, references `User`.
- [ ] **CAPA Workflow & Linking**:
    - [ ] Auto-create CAPA from NC when severity = CRITICAL or recurrence detected.
    - [ ] Link CAPA to A3: Problem-solving follows A3 methodology, CAPA tracks implementation.
    - [ ] Link CAPA to Standard Work: When corrective action requires procedure update, create linked StandardWork revision.
    - [ ] Closure gates: CAPA cannot close without:
        - [ ] Verification evidence (audit/test results).
        - [ ] Effectiveness check scheduled (30/60/90 days post-implementation).
        - [ ] Standard Work updated (if applicable).
    - [ ] Auto-reopen if effectiveness check fails.
- [ ] **8D Report Generation**:
    - [ ] Generate 8D PDF report from CAPA data:
        - [ ] D1: Team (CAPA owner + participants).
        - [ ] D2: Problem Description.
        - [ ] D3: Containment Actions.
        - [ ] D4: Root Cause Analysis (from linked A3 5-Why).
        - [ ] D5: Corrective Actions.
        - [ ] D6: Implementation Verification.
        - [ ] D7: Preventive Actions (Standard Work updates).
        - [ ] D8: Closure (team recognition, lessons learned).

#### 7.4.3. Inspection & Quality Checkpoints
- [ ] **InspectionPlan Model**: Quality inspection plan per product/station.
    - [ ] Fields: `id`, `product_id`, `station_id`, `inspection_type`, `sampling_plan`, `frequency`, `checkpoints_json`, `status`.
    - [ ] Inspection Type Enum: `INCOMING`, `IN_PROCESS`, `FINAL`, `PATROL`.
    - [ ] Sampling Plan: AQL-based sampling rules (sample size, accept/reject criteria).
    - [ ] Checkpoints JSON: Array of `{characteristic, specification, tolerance, measurement_method, gauge_id}`.
    - [ ] Relationships: references `Product`, references `Station`.
- [ ] **InspectionRecord Model**: Individual inspection results.
    - [ ] Fields: `id`, `inspection_plan_id`, `work_order_id`, `lot_number`, `sample_size`, `inspected_by`, `inspected_at`, `overall_result`, `measurements_json`, `notes`, `nc_id`.
    - [ ] Overall Result Enum: `PASS`, `FAIL`, `CONDITIONAL`.
    - [ ] Measurements JSON: Array of results per checkpoint.
    - [ ] Relationships: belongs to `InspectionPlan`, references `WorkOrder`, references `User`, optionally creates `NonConformance`.

### 7.5. Phase 3 Integration Points

#### 7.5.1. Cross-Module Linkages
- [ ] **Andon → A3**: Recurring Andon events auto-escalate to A3 problem solving.
- [ ] **NC → CAPA → A3**: Quality issues flow through structured problem-solving.
- [ ] **CAPA → Standard Work**: Corrective actions update standard work documents.
- [ ] **Training → Skills → Station Access**: Operators can only log work at stations where certified.
- [ ] **Work Order → CTQ**: Production linked to customer quality requirements.

#### 7.5.2. Obeya Integration
- [ ] **Shop Floor Metrics on Obeya**:
    - [ ] Delivery: Work order on-time completion rate.
    - [ ] Quality: NC rate (PPM), First Pass Yield, CAPA closure rate.
    - [ ] Cost: Scrap cost, rework hours.
    - [ ] People: Training compliance %, skill gap count.
- [ ] **Red Items from Production**:
    - [ ] Open critical Andon events > 4 hours.
    - [ ] Overdue CAPA actions.
    - [ ] Expired or expiring certifications.
    - [ ] WIP limit violations.

#### 7.5.3. Today Screen Integration
- [ ] **Shop Floor Priorities**:
    - [ ] Critical Andon events requiring acknowledgement.
    - [ ] Work orders at risk of missing due date.
    - [ ] CAPA verifications due today.
    - [ ] Training sessions scheduled today.
- [ ] **Abnormalities from Production**:
    - [ ] Stations with efficiency < target.
    - [ ] Cells with OEE < threshold.
    - [ ] Material Kanban cards overdue for replenishment.

### 7.6. Phase 3 Reporting & Analytics

#### 7.6.1. Production KPIs
- [ ] **OEE (Overall Equipment Effectiveness)**: Availability × Performance × Quality per cell/station.
- [ ] **First Pass Yield (FPY)**: Units passing first inspection / total units.
- [ ] **Takt Time Adherence**: Actual cycle time vs takt time.
- [ ] **Work Order On-Time Completion**: % completed by scheduled end date.
- [ ] **WIP Turn Rate**: Work orders completed / average WIP.

#### 7.6.2. Quality KPIs
- [ ] **NC Rate (PPM)**: Non-conformances per million units.
- [ ] **CAPA Closure Rate**: CAPAs closed on time / total CAPAs due.
- [ ] **CAPA Effectiveness Rate**: Effective CAPAs / total verified CAPAs.
- [ ] **Escape Rate**: Customer-detected defects / total shipped.
- [ ] **Inspection Yield**: Pass rate at each inspection stage.

#### 7.6.3. Training KPIs
- [ ] **Training Compliance**: % of required certifications current.
- [ ] **Skill Gap Index**: Required skills - Available skills per station.
- [ ] **Certification Expiration Rate**: Certifications expiring within 30 days.
- [ ] **Training Effectiveness**: Performance improvement post-training.

#### 7.6.4. Andon KPIs
- [ ] **MTTR (Mean Time To Resolution)**: Average time from Andon trigger to resolution.
- [ ] **Andon Frequency**: Events per shift/day by type and station.
- [ ] **Acknowledgement SLA Compliance**: % acknowledged within SLA.
- [ ] **A3 Escalation Rate**: % of Andon events escalated to A3.

---

## 8. AI Requirements (Section 12)

### 8.1. AI Features
- [ ] **Drafting**: Implement AI generation for "Missing Info" emails.
- [ ] **Summarization**: Implement Call-to-CTQ summarization.
- [ ] **Advisory**: Implement Qualification decision suggestions.
- [ ] **Learning**: Recommend micro-lessons based on user gaps.

### 8.2. AI Guardrails
- [ ] **UX**: Clearly label "AI Suggestion".
- [ ] **Confirmation**: Require explicit user confirmation for all AI actions.
- [ ] **Logging**: Log prompt context, model version, and user feedback.

### 8.3. AI Quality, Safety, and Evaluation (Enhancement)
- [ ] **Golden Test Set**: Build a small internal evaluation dataset (anonymized RFQs, quotes, CTQs) to regression-test AI behaviors.
- [ ] **Prompt/Context Hygiene**: Prevent unsafe instructions from attachments from changing system rules (treat attachments as data).
- [ ] **Human Feedback Loop**: Capture “accepted/edited/rejected” deltas to improve prompts and reduce repeated errors.

---

## 9. Non-Functional Requirements & UX

### 9.1. Performance & Reliability (Section 13)
- [ ] **Optimization**: Optimize database queries for search (< 1.5s).
- [ ] **Uptime**: Configure health checks and auto-scaling.
- [ ] **Backups**: Schedule automated DB backups with restore testing procedures.

### 9.2. Localization (Section 13.5)
- [ ] **i18n**: Implement support for English and French.
- [ ] **Formats**: Configure Date/Time/Currency for Morocco/Tunisia.

### 9.3. UX Refinement (Section 14)
- [ ] **Navigation**: Implement "Exceptions-first" dashboard design.
- [ ] **Mobile**: Verify mobile responsiveness for Today, Tasks, and Approvals.

### 9.4. Data Governance & Lifecycle (Enhancement)
- [ ] **Retention**: Define retention rules for attachments, audit logs, and learning records.
- [ ] **PII Controls**: Implement export/delete policies where appropriate and ensure access logs for sensitive fields.
- [ ] **Data Quality**: Add validation and required-field enforcement consistent with gates (RFQ completeness, qualification rationale).

### 9.5. Abuse Prevention & API Hardening (Enhancement)
- [ ] **Rate Limiting**: Add rate limiting and request size limits (especially file uploads).
- [ ] **Content Scanning**: Virus/malware scanning for uploaded attachments.
- [ ] **Secure Defaults**: CSRF protections (if cookie auth), secure headers, and dependency vulnerability scanning in CI.

---

## 10. Testing & Acceptance (Section 18)

### 10.1. Functional Testing
- [ ] Verify RFQ completeness gating.
- [ ] Verify Qualification approval logic.
- [ ] Verify Quote version immutability.
- [ ] Verify A3 closure requirements.

### 10.2. Usability Testing
- [ ] **New GM Onboarding**: Test "Day 1" flow.
- [ ] **Time-on-Task**: Measure RFQ intake (< 10 mins) and Quote Approval (< 60s).

### 10.3. Final Review
- [ ] **Deliverables Checklist**: Confirm all items in Section 21 are met.
- [ ] **Security Audit**: Verify RBAC and Audit Logs.

### 10.4. Automated Test Strategy (Enhancement)
- [ ] **Unit Tests**: Scoring rules, gating logic, versioning immutability, permissions matrix.
- [ ] **Integration Tests**: End-to-end object transitions (RFQ → Qualification → Quote → Release) with audit verification.
- [ ] **E2E Tests**: GM Day-1 flow (Today → overdue items → approvals → export snapshot).

### 10.5. Performance & Resilience Testing (Enhancement)
- [ ] **Load Tests**: Validate Today/Search latency targets under realistic data volume.
- [ ] **Chaos/Failure Modes**: Verify job retries, partial outages (storage down), and graceful degradation.
- [ ] **Disaster Recovery Drill**: Run a restore rehearsal and verify RPO/RTO targets.

---

## 11. Deployment, Operations, and Runbooks (Enhancement)

### 11.1. Production Readiness
- [ ] **Runbooks**: Document common operations (user provisioning, template updates, restoring backups).
- [ ] **Alerting**: Define alerts for job failures, slow queries, and PDF generation timeouts.
- [ ] **Access Reviews**: Implement periodic access reviews for GM/Admin roles.

### 11.2. Data Migration & Import (Enhancement)
- [ ] **CSV Import**: Import Accounts/Contacts/Opportunities from existing spreadsheets.
- [ ] **Deduplication**: Add basic duplicate detection for accounts/contacts.
- [ ] **Audit on Import**: Imported data should still produce audit entries.

### 11.3. Support, Incident Response, and Change Control (Enhancement)
- [ ] **Incident Flow**: Define severity levels and on-call/escalation path (even if small team).
- [ ] **Support Inbox**: Route user issues and feedback into A3-lite or Task creation.
- [ ] **Change Control**: Require approval + audit log for production changes to thresholds, margin floors, pipeline stages, and templates.

---

## 12. Simple, High-Value Features (Enhancement)

### 12.1. Speed and Focus (Premium UX)
- [ ] **Command Palette**: Global command palette (open RFQ/quote, create task, export snapshot) with fuzzy search.
- [ ] **Keyboard Shortcuts**: Power-user shortcuts for navigation, approvals, task completion, and exports.
- [ ] **Inline Validation**: Real-time validation with clear guidance (e.g., assumptions required before release).
- [ ] **Autosave Drafts**: Autosave for RFQ/Qualification/Quote drafts, with conflict handling.

### 12.2. Collaboration Without Noise
- [ ] **Activity Feed**: Object activity feed (changes, approvals, comments) with role-based visibility.
- [ ] **Mentions and Assignments**: Convert comments to tasks with one click, assign owners, set due dates.
- [ ] **Watch/Unwatch**: Watch key objects and notify only on meaningful changes.

### 12.3. Clean Data Operations
- [ ] **Bulk Actions**: Bulk update stage/owner/due dates for opportunities and tasks (RBAC governed).
- [ ] **Duplicate/Template From**: Create a quote from a previous quote version; create RFQ from a template.
- [ ] **CSV Export (MVP)**: Export pipeline and tasks to CSV.

### 12.4. Simple Additions With Big Impact
- [ ] **Inline PDF Preview**: Preview quote/qualification/Today PDFs in-app, tied to immutable versions.
- [ ] **Quick Actions Bar**: Context actions on every object (create task, request missing info, request approval, export).
- [ ] **GM Day-1 Setup Wizard**: Guided setup for stages, thresholds, roles, templates, first LSW cadence, first Obeya.
- [ ] **Data Hygiene Nudges**: Lightweight prompts when fields are missing (without blocking unless it’s a gate).

---

## 13. Premium UI System & Screen Design (Enhancement)

### 13.1. Design Principles (Non-Negotiables)
- [ ] **Premium Minimalism**: Fewer elements, more whitespace, clear hierarchy.
- [ ] **Typography-Led Hierarchy**: Use consistent type scale/weights instead of heavy borders.
- [ ] **Calm Surfaces**: Token-based surface layers (base/elevated/overlay) and subtle separators.
- [ ] **Precision Interactions**: Subtle motion, crisp hover/pressed states; never flashy.
- [ ] **Accessibility**: AA contrast targets, full keyboard navigation, screen-reader labels for workflows.

### 13.2. Design Tokens (Implementation Spec)
- [ ] **Token-First Styling**: All colors, radii, shadows, and spacing must use design tokens.
- [ ] **Core Tokens**: `--bg`, `--surface`, `--surface-2`, `--border`, `--text`, `--muted`, `--accent`, `--danger`, `--warning`, `--success`.
- [ ] **Elevation**: 3 levels only (flat, raised, overlay) with consistent shadow tokens.
- [ ] **Radii**: 2–3 radii steps to maintain a coherent feel.

### 13.3. Layout System
- [ ] **Global Shell**: Left nav (icons + labels) + top bar (search/command palette, org, user).
- [ ] **Content Grid**: Constrain width for readability; full-width only for boards.
- [ ] **Density Mode**: Comfortable default; optional compact mode.

### 13.4. Component Baseline (Premium)
- [ ] **Buttons**: primary/secondary/ghost/destructive with loading states.
- [ ] **Forms**: helper text + inline validation + predictable spacing.
- [ ] **Tables**: sticky header, row actions on hover, strong empty states.
- [ ] **Cards**: restrained chrome; avoid heavy shadows.
- [ ] **Badges/Chips**: consistent status chips for stages, severity, R/Y/G.
- [ ] **Timeline**: reusable timeline for audit + approvals.

### 13.5. Screen-by-Screen UI Spec (v1)
- [ ] **Today**: max 5 primary cards; Top 3 dominates; abnormalities compact and actionable; drill card lightweight.
- [ ] **Pipeline**: board/list toggle; stage totals; stale items shown as exceptions.
- [ ] **RFQ Detail**: completeness + missing items + attachments; Q&A + tasks; status + next action.
- [ ] **Qualification**: one-decision-per-screen; conditions drawer; rationale required.
- [ ] **Quote Builder**: sectioned layout; assumptions always visible; internal costing collapsible; pre-release checks summary.
- [ ] **CTQ Page**: structured CTQ cards with measurement/criteria + evidence links.
- [ ] **Obeya**: trends/exceptions only; red items enforce owner + due date; detail drawers.
- [ ] **A3-lite**: guided template, progressive disclosure, reflection required.
- [ ] **Learning**: calm progress; drills queue; no gamification.
- [ ] **Admin**: grouped by Gates/Approvals/Templates/Roles/Learning cadence.

### 13.6. Premium Fit-and-Finish Checklist
- [ ] Consistent empty/loading/error states with recovery guidance.
- [ ] Consistent microcopy + date/time/currency formatting.
- [ ] Prefer drawers over modals for detail; keep primary flow uninterrupted.

---

## 14. Learning Phase: Knowledge Acquisition + In-Software ML/Neural Networks (Enhancement)

### 14.1. Purpose
- [ ] Build an internal knowledge pack that powers micro-lessons, retrieval prompts, templates, and AI-assisted drafting.
- [ ] Ingest only explicitly permitted “free” resources (public domain or clearly licensed).

### 14.2. CLI Pulls (Open-License Only)
- [ ] **Ingestion CLI**: A CLI tool that pulls resources into a `knowledge_pack` store.
- [ ] **Allowed Licenses**: Accept only explicit permissive licenses (e.g., public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0).
- [ ] **License Verification**: Require license URL/text; store metadata per document (source, author, license, URL, retrieval date).
- [ ] **Attribution**: Display attribution wherever content is shown/used.
- [ ] **No-Paywall Rule**: Do not ingest copyrighted books/articles behind paywalls or unclear terms.

### 14.3. Processing Pipeline
- [ ] **Normalize**: Convert HTML/PDF/MD to clean text with headings preserved.
- [ ] **Chunk**: Heading-aware semantic chunking; store chunk provenance and citations.
- [ ] **Filter**: Deduplicate, remove boilerplate, flag low-quality chunks.
- [ ] **Tag**: Tag chunks to taxonomy (TPS, PDCA, Kata, quoting, qualification, CTQ, obeya).

### 14.4. Neural/ML Components (In-Software)
- [ ] **Embeddings**: Run an open embedding model to vectorize chunks.
- [ ] **Vector Index**: Build a semantic index to retrieve guidance based on workflow context.
- [ ] **Lightweight Models**: Train/maintain small models (or hybrid rules+ML) for:
  - [ ] lesson/drill recommendation,
  - [ ] missing-evidence detection (which gate will fail),
  - [ ] condition suggestions for qualification.
- [ ] **Drafting (Optional)**: Draft emails/A3 text strictly from approved knowledge + current object data (human confirmation required).

### 14.5. MLOps and Safety
- [ ] **Versioning**: Version models + indices; support rollbacks.
- [ ] **Evaluation**: Regression tests against a golden set before promoting.
- [ ] **Safety Gates**: Block outputs that reference unknown/unlicensed sources; keep attachments as data, not instructions.

---

## 15. Hetzner Deployment + Client App (Enhancement)

### 15.1. Hetzner-Friendly Architecture
- [ ] **Docker Compose**: Run `web`, `api`, `worker`, `db`, `cache/queue`, `object-storage`.
- [ ] **Reverse Proxy**: Caddy/Traefik for TLS and routing.
- [ ] **PostgreSQL**: backups + restore drills; isolate DB network.
- [ ] **Redis**: job queue + caching.
- [ ] **Object Storage**: S3-compatible storage (Hetzner/MinIO) for attachments and exports.
- [ ] **Firewall**: only 80/443 public; keep DB/cache private.

### 15.2. Client App (Comfortable)
- [ ] **Primary**: installable PWA (fast iteration, offline support).
- [ ] **Optional Native Wrapper**: Capacitor wrapper for a “real app” feel (camera, file uploads, push notifications).
- [ ] **Mobile Flows**: Today/Approvals/Tasks/A3 capture optimized for one-hand use.

---

## 16. Phase 1 MVP Cutline & Milestones (Enhancement)

### 16.1. MVP Cutline (Must Ship)
- [ ] **Core Objects**: Users/RBAC, Accounts/Contacts, Opportunities, RFQs (completeness + tasks), Qualification (decision + rationale + override), Quotes (versioning + assumptions + approvals + PDF), CTQs, Obeya, A3-lite, Learning prompts, Admin configuration.
- [ ] **Cadence**: Today screen + LSW checklist + daily snapshot export.
- [ ] **Auditability**: Approval logs + overrides with rationale.

### 16.2. Next After MVP
- [ ] Supplier portal lite, OCR ingestion, collaboration comments, what-if simulation, PWA offline mode, advanced KPI slicing.

### 16.3. Suggested Milestones
- [ ] **M1 (Foundation)**: Auth/RBAC, schema, migrations, basic CRUD.
- [ ] **M2 (RFQ → Qualification)**: RFQ gates + tasks + qualification + export.
- [ ] **M3 (Quote → Release)**: quote builder, approvals, versioning, PDF.
- [ ] **M4 (GM OS)**: Today + LSW + Obeya + A3 triggers + learning drill.
- [ ] **M5 (Hardening)**: security tests, backups/restore drill, performance targets, runbooks.

---

## 17. Release Acceptance Gates (Enhancement)

### 17.1. Functional Gates
- [ ] RFQ cannot enter Qualification without threshold or override rationale.
- [ ] Qualification/Quote approvals enforce rationale, role permissions, and are fully auditable.
- [ ] Quote versions are immutable and PDFs bind to versions.
- [ ] A3 cannot close without reflection + standard/checklist update (or justification).

### 17.2. Non-Functional Gates
- [ ] Today screen latency meets target; search is responsive at expected volume.
- [ ] Backup + restore drill passes and is documented.
- [ ] RBAC verification suite passes; audit logs behave append-only for critical actions.

---

**End of Development Plan**
