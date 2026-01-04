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

### 7.1. Standard Work & Training (Section 10.1, 10.2)
- [ ] **Standard Work**: Implement versioned document management linked to Product/Station.
- [ ] **Training Matrix**:
    - [ ] Map Roles to Skills.
    - [ ] Track User status (Trained/Certified) and Recertification dates.

### 7.2. Shop Floor Control (Section 10.3, 10.5)
- [ ] **Andon System**:
    - [ ] Event logging: Station, Product, Symptom, Photo.
    - [ ] Workflow: Stop-Call-Wait logic.
    - [ ] Auto-escalate to A3 on recurrence.
- [ ] **Kanban**: Implement Digital Kanban cards and WIP Limit logic per cell.

### 7.3. Quality Management (Section 10.4)
- [ ] **NC/CAPA**:
    - [ ] Non-conformance recording.
    - [ ] Disposition workflow.
    - [ ] Link CAPA to A3 and Standard Work.

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
