# Comprehensive Backend Data Models Map

> **Generated from**: `backend/src/sensei/models/` (50+ Python files)  
> **Framework**: SQLAlchemy 2.0 ORM (async mode, `AsyncAttrs`, `DeclarativeBase`)  
> **Database**: PostgreSQL with JSONB, UUID, pgvector extensions  
> **Total tables**: ~200+

---

## Table of Contents

1. [Base Infrastructure](#1-base-infrastructure)
2. [Authentication & RBAC](#2-authentication--rbac)
3. [CRM — Accounts & Contacts](#3-crm--accounts--contacts)
4. [Sales Pipeline — Opportunities, RFQs, Quotes](#4-sales-pipeline--opportunities-rfqs-quotes)
5. [Qualification & CTQ](#5-qualification--ctq)
6. [Risk Management](#6-risk-management)
7. [Project Management](#7-project-management)
8. [Obeya & A3](#8-obeya--a3)
9. [Tasks & Notifications](#9-tasks--notifications)
10. [Products & BOM & Routing](#10-products--bom--routing)
11. [Work Centers & Stations](#11-work-centers--stations)
12. [Work Orders & Operations](#12-work-orders--operations)
13. [Production & Cells](#13-production--cells)
14. [Kanban System](#14-kanban-system)
15. [Andon System](#15-andon-system)
16. [Standard Work](#16-standard-work)
17. [Quality — NC, CAPA, Inspection](#17-quality--nc-capa-inspection)
18. [Quality — QMS](#18-quality--qms)
19. [Maintenance & Assets](#19-maintenance--assets)
20. [Inventory & WMS](#20-inventory--wms)
21. [MRP & MPS](#21-mrp--mps)
22. [Finance & GL](#22-finance--gl)
23. [Accounts Payable](#23-accounts-payable)
24. [Accounts Receivable & Shipping](#24-accounts-receivable--shipping)
25. [HR & Benefits (North Africa)](#25-hr--benefits-north-africa)
26. [Training & Skills](#26-training--skills)
27. [Learning System](#27-learning-system)
28. [Analytics & KPIs](#28-analytics--kpis)
29. [AI/ML Models](#29-aiml-models)
30. [Cognitive Obeya (AI)](#30-cognitive-obeya-ai)
31. [Strategic Analytics (AI)](#31-strategic-analytics-ai)
32. [TPS Gamification](#32-tps-gamification)
33. [Admin & Configuration](#33-admin--configuration)
34. [Attachments & Audit Trail](#34-attachments--audit-trail)
35. [Data Lineage & AI Reasoning](#35-data-lineage--ai-reasoning)
36. [PII & Privacy](#36-pii--privacy)
37. [Segments & Saved Views](#37-segments--saved-views)
38. [Service Persistence](#38-service-persistence)
39. [Knowledge Packs](#39-knowledge-packs)
40. [OT Network Security](#40-ot-network-security)
41. [Business Continuity / DR](#41-business-continuity--dr)
42. [Data Migration](#42-data-migration)
43. [Sites](#43-sites)
44. [Exceptions](#44-exceptions)
45. [Cross-Model Relationship Diagram](#45-cross-model-relationship-diagram)

---

## 1. Base Infrastructure

**File**: `base.py`

All models inherit from `Base` (UUID primary key via `uuid4`). Common mixins:

| Mixin | Fields | Type |
|-------|--------|------|
| **TimestampMixin** | `created_at`, `updated_at` | DateTime (auto) |
| **AuditMixin** | `created_by_id` → FK `users.id`, `updated_by_id` → FK `users.id`, `owner_id` → FK `users.id` | UUID FK |
| **SoftDeleteMixin** | `deleted_at`, `deleted_by_id` → FK `users.id` | DateTime, UUID FK |
| **StatusMixin** | `status` | String |

Helper: `generate_ulid()` for ULID-based identifiers.

**RBAC note**: Every model using `AuditMixin` has `created_by_id`, `updated_by_id`, `owner_id` linking to `users`.

---

## 2. Authentication & RBAC

**File**: `user.py`

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email | String(255) | unique, index |
| username | String(100) | unique |
| password_hash | String(255) | |
| first_name, last_name | String(100) | |
| display_name | String(200) | |
| avatar_url | String(500) | |
| phone | String(50) | |
| department | String(100) | |
| job_title | String(100) | |
| status | Enum(UserStatus) | active/inactive/suspended/pending |
| is_superuser | Boolean | **RBAC** |
| email_verified | Boolean | |
| totp_secret | String(255) | MFA |
| totp_enabled | Boolean | |
| backup_codes | JSONB | |
| last_login_at | DateTime | |
| last_activity_at | DateTime | |
| failed_login_attempts | Integer | |
| locked_until | DateTime | |
| password_changed_at | DateTime | |
| must_change_password | Boolean | |
| preferences | JSONB | |
| locale | String(10) | |
| timezone | String(50) | |
| + AuditMixin, TimestampMixin, SoftDeleteMixin | | |

**Relationships**: roles → `UserRole`, tasks_assigned, tasks_created, notifications

### `roles`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | String(100) | unique |
| display_name | String(200) | |
| description | Text | |
| role_type | Enum(RoleType) | **24 types**: ADMIN, GM, OPERATIONS_MGR, QUALITY_MGR, ENGINEERING_MGR, SALES_MGR, FINANCE_MGR, HR_MGR, PRODUCTION_MGR, MAINTENANCE_MGR, WAREHOUSE_MGR, PROJECT_MGR, TEAM_LEAD, ENGINEER, QUALITY_INSPECTOR, OPERATOR, SALES_REP, BUYER, ACCOUNTANT, HR_SPECIALIST, MAINTENANCE_TECH, WAREHOUSE_WORKER, AI_AGENT, VIEWER |
| is_system | Boolean | |
| is_active | Boolean | |
| hierarchy_level | Integer | 0=ADMIN → 100=VIEWER |

### `permissions`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | String(200) | unique |
| display_name | String(200) | |
| resource | String(100) | **RBAC**: e.g., "rfq", "quote" |
| action | String(50) | **RBAC**: e.g., "create", "read", "update", "delete" |
| is_system | Boolean | |
| UniqueConstraint | | (resource, action) |

### `user_roles`
| Column | Type | Notes |
|--------|------|-------|
| user_id | UUID FK → users | |
| role_id | UUID FK → roles | |
| assigned_at | DateTime | |
| assigned_by_id | UUID FK → users | |
| expires_at | DateTime | nullable |
| is_active | Boolean | |

### `role_permissions`
| Column | Type | Notes |
|--------|------|-------|
| role_id | UUID FK → roles | |
| permission_id | UUID FK → permissions | |
| conditions | JSONB | **RBAC**: conditional permissions |

### `refresh_tokens`
| Column | Type | Notes |
|--------|------|-------|
| user_id | UUID FK → users | |
| token_hash | String(255) | |
| expires_at | DateTime | |
| issued_at | DateTime | |
| device_info, ip_address, user_agent | String | |
| is_revoked | Boolean | |
| revoked_at, revoked_reason | | |

---

## 3. CRM — Accounts & Contacts

**File**: `account.py`

### `accounts`
| Column | Type | Notes |
|--------|------|-------|
| name | String(255) | |
| legal_name | String(255) | |
| account_number | String(50) | unique |
| account_type | Enum | customer/prospect/supplier/partner/competitor |
| status | Enum | active/inactive/suspended |
| tier | Enum | strategic/key/standard/small |
| industry, sub_industry | String | |
| website, phone, fax, email | String | |
| address, city, state, postal_code, country | String | default country="Morocco" |
| tax_id, registration_number | String | |
| employees_count | Integer | |
| annual_revenue | Numeric(18,2) | |
| revenue_currency | String(3) | default "MAD" |
| lead_source | String | |
| capabilities | JSONB | |
| certifications | JSONB | |
| qualification_score, health_score | Numeric | |
| parent_id | UUID FK → accounts (self) | hierarchy |
| + AuditMixin, SoftDeleteMixin | | |

**Relationships**: parent, subsidiaries, contacts (via `AccountContact`), opportunities, rfqs, supplier_quotes, work_centers

### `contacts`
| Column | Type | Notes |
|--------|------|-------|
| first_name, last_name, middle_name | String | |
| salutation, suffix | String | |
| email, secondary_email | String | |
| phone, mobile, fax | String | |
| job_title, department | String | |
| preferred_language, timezone | String | |
| linkedin_url, twitter_handle | String | |
| email_opt_out, do_not_call | Boolean | |
| custom_fields | JSONB | |

### `account_contacts`
| Column | Type | Notes |
|--------|------|-------|
| account_id | UUID FK → accounts | |
| contact_id | UUID FK → contacts | |
| role | Enum(ContactRole) | |
| is_primary, is_active | Boolean | |

---

## 4. Sales Pipeline — Opportunities, RFQs, Quotes

### `opportunities` (opportunity.py)
| Key Columns | Type | Notes |
|-------------|------|-------|
| opportunity_number | String | unique |
| account_id | FK → accounts | |
| primary_contact_id | FK → contacts | |
| stage | Enum(OpportunityStage) | prospecting→closed_won/lost |
| amount, currency(MAD), probability | Numeric, String | |
| weighted_amount | Numeric | |
| close_date | Date | |
| competitor_id | FK → accounts | |
| partner_id | FK → accounts | |
| part_numbers, processes_required, materials | JSONB | |
| + AuditMixin, SoftDeleteMixin | | |

### `opportunity_notes`
| opportunity_id, note_type, content, author_id | | |

### `rfqs` (rfq.py) 🤖
| Key Columns | Type | Notes |
|-------------|------|-------|
| rfq_number | String | unique |
| account_id | FK → accounts | |
| contact_id | FK → contacts | |
| opportunity_id | FK → opportunities | |
| status | Enum(RFQStatus) | draft→won/lost/no_bid |
| part_number, part_name, drawing_number | String | |
| quantity, annual_volume | Integer | |
| target_price, currency(MAD) | Numeric | |
| material_spec, tolerance_requirements | String | |
| primary_process, secondary_processes | String, JSONB | |
| certifications_required | JSONB | |
| assigned_to_id | FK → users | |
| triage_risk_score | Numeric | AI |
| clarification_draft_email | Text | AI |
| **embedding** | **Vector(384)** | **AI: pgvector semantic search** |
| + AuditMixin, SoftDeleteMixin | | |

### `rfq_questions`, `rfq_attachments`

### `quotes` (quote.py) 🤖
| Key Columns | Type | Notes |
|-------------|------|-------|
| quote_number | String | unique |
| rfq_id | FK → rfqs | |
| opportunity_id | FK → opportunities | |
| account_id | FK → accounts | |
| status | Enum(QuoteStatus) | |
| currency(MAD), subtotal, total, total_cost | Numeric | |
| target_margin, actual_margin | Numeric | |
| approval_status, approved_by_id | FK → users | **RBAC** |
| **embedding** | **Vector(384)** | **AI: pgvector semantic search** |
| + AuditMixin, SoftDeleteMixin | | |

### `quote_versions`, `quote_line_items`, `supplier_quotes`, `supplier_quote_items`

### Quoting Helpers (quoting_helper.py)
- `work_packets` — RFQ discipline work items (EE/ME/MfgE/QE/Purchasing)
- `pcb_specs` — PCB specifications linked to RFQ
- `rfq_package_versions` — RFQ document versioning
- `rate_cards` — Labor/overhead rate configurations
- `quote_actuals` — Quoted vs actual cost comparison

---

## 5. Qualification & CTQ

### `qualifications` (qualification.py)
| Key Column | Type | Notes |
|------------|------|-------|
| rfq_id | FK → rfqs | |
| result | Enum(QualificationResult) | pass/conditional/fail |
| total_score, percentage_score | Numeric | |
| pass_threshold (70), conditional_threshold (50) | Numeric | |
| category_scores | JSONB | |
| has_blockers, blocker_reasons | Boolean, JSONB | |
| reviewed_by_id, approved_by_id | FK → users | **RBAC** |

### `qualification_criteria`, `qualification_scores`

### `ctqs` (ctq.py)
| Key Column | Type | Notes |
|------------|------|-------|
| rfq_id | FK → rfqs | |
| ctq_number, name, part_number | String | |
| nominal_value, upper/lower_spec_limit | Numeric | |
| tolerance_type | String | |
| cpk_target, ppk_target | Numeric | SPC |
| measurement_method/equipment | String | |
| gauge_r_and_r | Numeric | |
| approved_by_id | FK → users | **RBAC** |

### `ctq_measurements`

---

## 6. Risk Management

**File**: `risk.py`

### `risks`
| Key Column | Type | Notes |
|------------|------|-------|
| risk_number | String | unique |
| related_entity_type/id | String, UUID | **polymorphic** |
| rfq_id | FK → rfqs | |
| category, status | String | |
| inherent/residual likelihood/severity/scores | Numeric | |
| potential_cost, potential_delay_days | Numeric | |
| root_causes, potential_effects | JSONB | |
| response_strategy | String | |
| risk_owner_id | FK → users | **RBAC** |

### `risk_mitigations`

---

## 7. Project Management

**File**: `project_management.py`

### `projects`
| Key Column | Type | Notes |
|------------|------|-------|
| name, slug | String | |
| project_type | Enum(ProjectType) | NPI, KAIZEN, A3, MAINTENANCE, etc. |
| owner_id | FK → users | **RBAC** |
| is_private | Boolean | **RBAC** |
| related_rfq_id, related_work_order_id, related_a3_id | FK | cross-links |
| settings (sprint_duration, use_story_points) | via columns | |

### `project_members`
| Column | Type | Notes |
|--------|------|-------|
| project_id | FK → projects | |
| user_id | FK → users | |
| role | String | admin/member/viewer/guest — **RBAC** |
| can_edit, can_comment, can_invite, can_delete | Boolean | **RBAC** |

### `epics`, `user_stories`, `subtasks`
### `story_comments`, `story_history`
### `sprints`, `milestones`
### `issues`, `issue_comments`
### `wiki_pages`, `project_activity`, `board_views`

---

## 8. Obeya & A3

### `obeya_items` (obeya.py)
| Key Column | Type | Notes |
|------------|------|-------|
| board, column, position | String, Int | |
| related_entity_type/id | String, UUID | **polymorphic** |
| assigned_to_id | FK → users | |
| KPI target/actual/unit fields | Numeric | |

### `obeya_comments`

### `a3s` (a3.py)
| Key Column | Type | Notes |
|------------|------|-------|
| a3_number | String | unique |
| a3_type | String | problem_solving/proposal/status |
| related_entity_type/id | String, UUID | **polymorphic** |
| author_id, sponsor_id, coach_id | FK → users | **RBAC** |
| team_members | JSONB | |
| approval fields | | **RBAC** |

### `a3_sections`

---

## 9. Tasks & Notifications

**File**: `task.py`

### `tasks`
| Key Column | Type | Notes |
|------------|------|-------|
| related_entity_type/id | String, UUID | **polymorphic** |
| assignee_id | FK → users | |
| created_by_id | FK → users | |
| task_type, status, priority | Enum | |
| recurring fields | | |
| checklist, attachments | JSONB | |

### `task_comments`

### `notifications`
| Key Column | Type | Notes |
|------------|------|-------|
| user_id | FK → users | |
| title, message | String | |
| notification_type | String | |
| related_entity_type/id | String, UUID | **polymorphic** |
| is_read | Boolean | |

---

## 10. Products & BOM & Routing

**File**: `product.py`

### `products` (UUID PK)
| Key Column | Type | Notes |
|------------|------|-------|
| name, part_number, sku, revision | String | |
| category, product_family | String | |
| unit_of_measure | Enum(UnitOfMeasure) | |
| weight_kg, dimensions | Numeric, JSONB | |
| standard_cost, unit_cost | Numeric | |
| standard_labor_hours | Numeric | |
| lead_time_days, setup_time_hours | Numeric | |
| reorder_point, safety_stock | Numeric | |
| status | Enum(ProductStatus) | |

### `bom_items` (Int PK)
| product_id FK, component_product_id FK, quantity, scrap_factor | |

### `routings` (Int PK)
| product_id FK, station_id FK, sequence, operation_name, standard_time_seconds, labor_hours | |

---

## 11. Work Centers & Stations

**File**: `work_center.py`

### `work_centers` (Int PK)
| Key Column | Type | Notes |
|------------|------|-------|
| name, code | String | |
| capacity_units, capacity_value | String, Numeric | |
| efficiency_target | Numeric | |
| status | Enum(WorkCenterStatus) | |
| account_id | FK → accounts | |

### `stations` (Int PK)
| Key Column | Type | Notes |
|------------|------|-------|
| name, code | String | |
| station_type | Enum(StationType) | |
| takt_time_seconds, cycle_time_seconds, setup_time_seconds | Integer | |
| yellow_ack_minutes, red_ack_minutes | Integer | Andon SLA |
| resolution_target_minutes | Integer | |
| work_center_id | FK → work_centers | |
| production_cell_id | FK → production_cells | |

---

## 12. Work Orders & Operations

**File**: `work_order.py`

### `work_orders` (Int PK)
| Key Column | Type | Notes |
|------------|------|-------|
| work_order_number | String | unique |
| quote_id | FK → quotes | |
| sales_order_id | FK → sales_orders | |
| rfq_id | FK → rfqs | |
| account_id | FK → accounts | |
| product_id | FK → products | |
| quantity_ordered/completed/scrapped/in_progress | Numeric | |
| status | Enum(WorkOrderStatus) | |
| work_center_id | FK → work_centers | |
| current_station_id | FK → stations | |
| lot_number, batch_id | String | |

### `work_order_operations` (Int PK)
| work_order_id FK, routing_id FK, station_id FK, operator_id FK → users, status, quantities, timing | |

---

## 13. Production & Cells

**File**: `production.py`

### `production_cells` (Int PK)
| name, code, work_center_id FK, cell_type, takt/cycle times, target_output_per_shift, operator staffing (min/std/max/current), current OEE fields | |

### `cell_performances` (Int PK)
| cell_id FK, shift_date, shift_number, output, quality, OEE metrics | **Analytics** |

### `shift_handover_notes` (Int PK)
| station_id FK, work_order_id FK, SQDCP fields (safety/quality/delivery/cost/people) | |

### `global_pulses` (Int PK)
| message, severity, is_active, highlight metric fields | |

---

## 14. Kanban System

**File**: `kanban.py`

### `kanban_boards` (Int PK)
| Key Column | Type | Notes |
|------------|------|-------|
| name, code | String | |
| board_type | Enum(BoardType) | production/material/engineering/maintenance/project/improvement |
| work_center_id | FK → work_centers | |
| wip_limit_global | Integer | |
| columns_config_json | JSONB | column names, WIP limits, colors |
| swimlanes_config_json | JSONB | |

### `kanban_cards` (Int PK)
| board_id FK, column_name, card_type (Enum), priority, status, work_order_id FK, product_id FK, assigned_to_id FK → users, cycle time tracking, story_points, wip_limit_override (Boolean + override_by FK → users) | |

### `kanban_card_history` (Int PK)
| card_id FK, field_name, old/new_value, changed_by_id FK → users | |

### `kanban_metrics` (Int PK) — **Analytics**
| board_id FK, metric_date, cards_completed, wip_count, avg_cycle/lead_time, column_snapshots (JSONB) | |

---

## 15. Andon System

**File**: `andon.py`

### `andon_events` (Int PK)
| Key Column | Type | Notes |
|------------|------|-------|
| event_number | String | unique |
| andon_type | Enum(AndonType) | quality/equipment/material/safety/process/information/support |
| severity | Enum(Severity) | |
| station_id | FK → stations | |
| product_id | FK → products | |
| work_order_id | FK → work_orders | |
| reported_by_id | FK → users | |
| acknowledged_by_id | FK → users | |
| resolved_by_id | FK → users | |
| escalated_to_a3_id | FK → a3s | cross-link |
| downtime_minutes | Integer | |
| estimated_cost_impact | Numeric | |
| is_recurrence, related_event_id | Boolean, FK self | |

### `andon_escalations` (Int PK)
| andon_event_id FK, escalation_level, escalated_to_user_id FK → users, delegated_to_user_id FK → users | |

### `andon_recurrence_patterns` (Int PK)
| station_id FK, andon_type, symptom_pattern, occurrence_count, escalation_threshold, a3_id FK → a3s | |

---

## 16. Standard Work

**File**: `standard_work.py`

### `standard_works` (Int PK)
| document_number, title, version, revision_code, document_type (Enum), status, product_id FK, station_id FK, content_json (JSONB steps), submitted_by_id FK → users, approved_by_id FK → users, requires_training, previous_version_id FK self | **RBAC**: approval workflow |

### `standard_work_versions` (Int PK)
| standard_work_id FK, version, content_json, created_by_id FK → users | |

---

## 17. Quality — NC, CAPA, Inspection

**File**: `quality.py`

### `non_conformances` (Int PK)
| nc_number, nc_type, severity, product_id FK, work_order_id FK, station_id FK, detected_by_id FK → users, root_cause fields, disposition fields, capa_id FK, supplier_id FK → accounts, cost_impact/scrap_cost/rework_cost | |

### `capas` (Int PK)
| capa_number, capa_type, source, severity, status, related_nc_id FK, linked_standard_work_id FK, owner_id FK → users | **RBAC** |

### `capa_actions` (Int PK)
| capa_id FK, assigned_to_id FK → users, due_date, verification fields | |

### `inspection_plans`, `inspection_records`

---

## 18. Quality — QMS

**File**: `quality_qms.py` (34 tables)

### Document Control
- `qms_documents` — doc_type, doc_number, owner_id FK → users, current_revision_id
- `qms_document_revisions` — document_id FK, revision_code, status, signatures (JSONB)
- `qms_external_documents` — external standards/specs tracking

### Supplier Quality
- `qms_supplier_scorecards` — supplier_id FK → accounts, period_key, ppm, otd, copq — **Analytics**
- `qms_scars` (Supplier Corrective Actions) — supplier_id FK, related_nc_id FK, related_capa_id FK

### Auditing
- `qms_audits` — audit_type, supplier_id FK, checklist_json
- `qms_audit_findings` — severity, assigned_to_id FK → users, linked_nc_id FK, linked_capa_id FK

### Metrology
- `qms_gauges` — gauge_number, calibration_interval, owner_id FK → users
- `qms_calibration_events` — gauge_id FK, performed_by_id FK → users, out_of_cal

### MSA (Measurement System Analysis)
- `qms_msa_studies` — gauge_id FK, parts/operators/trials counts
- `qms_msa_measurements` — study_id FK, operator_id FK → users, measured_value
- `qms_msa_results` — repeatability, reproducibility, GR&R%, NDC

### Process Capability
- `qms_process_capability_studies` — LSL, USL, target
- `qms_process_capability_measurements`, `qms_process_capability_results` — Cp, Cpk, Cpu, Cpl

### First Article Inspection (AS9102)
- `qms_first_article_inspections` — product_id FK, work_order_id FK, inspector_id FK → users
- `qms_fai_characteristics` — nominal, tolerance, actual, tool_id FK → gauges

### Self-Inspection
- `qms_self_inspections` — operator_id FK → users
- `qms_self_inspection_checks`

### Laboratory
- `qms_lab_test_methods` — standard (ASTM/ISO), spec limits
- `qms_lab_samples` — product_id FK, collected_by_id FK → users
- `qms_lab_test_runs` — method_id FK, tester_id FK → users

### AQL Sampling
- `qms_aql_sampling_plans` — ANSI/ASQ Z1.4 parameters
- `qms_aql_lot_inspections` — accept/reject limits, inspector_id FK → users

### Traceability
- `qms_traceability_matrices` — product_id FK, work_order_id FK, lot_number
- `qms_traceability_links` — polymorphic links

### Change Point Studies
- `qms_change_point_studies`, `qms_change_point_observations`, `qms_change_point_events`

### Management Reviews
- `qms_management_reviews` — metrics_snapshot (JSONB), attendees (JSONB)
- `qms_management_review_actions` — assignee_id FK → users

### Customer Quality
- `qms_customer_complaints` — customer_id FK → accounts, related_nc_id FK, related_capa_id FK
- `qms_customer_surveys` — NPS surveys
- `qms_customer_survey_responses` — customer_id FK → accounts, nps_score

---

## 19. Maintenance & Assets

**File**: `maintenance.py`

### `maintenance_assets`
| asset_number, name, asset_type, criticality (A/B/C), work_center_id FK, station_id FK, parent_asset_id FK self, operating_hours, next_pm_date | |

### `pm_schedules`
| asset_id FK, frequency_type/value/unit, checklist/skills/safety/parts (JSONB) | |

### `maintenance_work_orders`
| asset_id FK, type, priority, pm_schedule_id FK, assigned_to_id FK → users, approval fields | |

### Additional maintenance tables:
- `maintenance_labor_entries`, `maintenance_parts_used`, `maintenance_spare_parts`
- `maintenance_downtime_events`
- `maintenance_failure_records`
- `condition_readings` — **PARTITIONED by RANGE on created_at**
- `maintenance_records`
- `maintenance_loto_procedures`, `maintenance_loto_energy_sources`, `maintenance_loto_locks`
- `maintenance_tool_items`, `maintenance_tool_checkouts`

---

## 20. Inventory & WMS

**File**: `inventory.py`

### Core Inventory
- `inventory_warehouses` — name, code (unique)
- `inventory_locations` — warehouse_id FK, parent_id FK self (hierarchical), location_type
- `inventory_levels` — product_id FK → products, location_id FK, quantity_on_hand, quantity_reserved, lpn_id FK
- `inventory_stock_moves` — product_id FK, source/destination locations FK, quantity, lpn_id FK
- `inventory_valuation_layers` — stock_move_id FK, unit_cost, value

### WMS (Warehouse Management)
- `wms_license_plates` (LPN) — number (unique), location_id FK, parent_lpn_id FK self
- `wms_workstations` — warehouse_id FK, scanner_model, station_type
- `wms_devices` — warehouse_id FK, device_type, capabilities (JSONB)
- `pick_lists` — warehouse_id FK, source_type/id (polymorphic), assigned_to_id FK → users, device_id FK, pick_strategy
- `pick_list_lines` — pick_list_id FK, sku, source/target location FKs, lpn_id FK

---

## 21. MRP & MPS

**File**: `mrp.py`

- `mrp_bom_components` — parent_product_id FK, component_product_id FK, quantity_per, scrap_factor
- `mrp_demands` — product_id FK, demand_type (sales_order/forecast/safety_stock/work_order)
- `mrp_suggestions` — product_id FK, requirement_type (buy/build), approved_by_id FK → users
- `mrp_runs` — executed_by_id FK → users, suggestions/shortages counts
- `mps_plans` — name, period_start/end
- `mps_plan_lines` — plan_id FK, product_id FK, bucket_date, quantity

---

## 22. Finance & GL

**File**: `finance.py`

### General Ledger
- `gl_accounts` — account_code, account_type, parent_id FK self, normal_balance
- `opening_balances` — account_id FK, debit/credit/net_amount
- `accounting_periods` — period_key, status (open/closed)
- `journal_entries` — status (draft/approved/posted/reversed), approved_by, posted_by
- `journal_lines` — entry_id FK, account_id FK, debit, credit

### FX & Currency
- `fx_rates` — from/to_currency, rate
- `finance_currency_settings` — base/reporting_currency, allowed_currencies (JSONB)
- `currencies` — code, name, symbol

### Cost Accounting
- `standard_costs` — product_id FK, material/labor/overhead/total_unit_cost
- `work_order_cost_rollups` — work_order_id FK, actual costs, variances

### Tax
- `tax_jurisdictions`, `tax_rates`, `tax_transactions`

### Banking
- `payment_terms`, `bank_accounts` (site_id FK, gl_account_id FK), `bank_transactions`

---

## 23. Accounts Payable

**File**: `accounts_payable.py`

- `purchase_requisitions` — pr_number, requested_by_id/submitted_by_id/approved_by_id/rejected_by_id all FK → users, supplier_id FK → accounts
- `pr_lines` — pr_id FK, sku, quantity, unit_price
- `purchase_orders` — po_number, supplier_id FK → accounts, source_pr_id FK, approved_by_id FK → users
- `po_lines` — po_id FK
- `goods_receipts` — po_id FK, received_by_id FK → users
- `receipt_lines` — receipt_id FK
- `supplier_invoices` — supplier_id FK → accounts, po_id FK, approved_by_id/posted_by_id/paid_by_id FK → users
- `supplier_invoice_lines`
- `payment_runs` — approved_by_id/executed_by_id FK → users
- `payments` — supplier_id FK → accounts
- `payment_invoice_links` — M2M (payment_id, invoice_id)

---

## 24. Accounts Receivable & Shipping

**File**: `accounts_receivable.py`

- `customer_credit_profiles` — account_id FK (PK), credit_limit, is_on_credit_hold
- `sales_orders` — account_id FK → accounts, source_quote_id FK → quotes, approved_by_id FK → users
- `sales_order_lines`
- `customer_invoices` — account_id FK, sales_order_id FK, is_credit_memo, disputed
- `customer_invoice_lines`
- `payment_receipts` — account_id FK, received_by_id FK → users
- `payment_allocations` — receipt_id FK, invoice_id FK
- `invoice_disputes` — invoice_id FK, opened_by_id/resolved_by_id FK → users
- `shipments` — sales_order_id FK, account_id FK, ship_from_warehouse_id FK, carrier, tracking fields, ship_to address, default country="Tunisia"
- `shipment_lines` — sales_order_line_id FK

---

## 25. HR & Benefits (North Africa)

**File**: `hr.py` (33 tables)

### Core HR
- `hr_employees` — user_id FK → users (1:1), first/last_name, department, job_title, site_id, manager_id FK self, jurisdiction (TN/MA/EG), cost_center_code, status, hire/termination dates
- `hr_checklists` — employee_id FK, checklist_type (onboarding/offboarding), items_json (JSONB)
- `hr_job_openings` — hiring_manager_id FK → users
- `hr_job_applications` — job_opening_id FK
- `hr_appraisals` — employee_id FK, appraiser_id FK → users, score
- `hr_leave_requests` — employee_id FK, leave_type, approved_by_id FK → users

### North Africa Social Security (Tunisia/Morocco/Egypt)
- `hr_jurisdiction_configs` — jurisdiction (TN/MA/EG) unique, employee/employer rates (pension, health, unemployment, family, work_injury), contribution caps, leave entitlements, retirement ages
- `hr_social_security_records` — employee_id FK, jurisdiction, ss_number, employment_type, sector_type, is_arduous/dangerous_work, contribution days/months
- `hr_contribution_periods` — ss_record_id FK, gross_earnings, employee/employer contribution breakdowns, payment_status
- `hr_family_allowances` — employee_id FK, jurisdiction, eligible_children, dependents_json (JSONB), monthly_allowance
- `hr_sickness_maternity_benefits` — employee_id FK, benefit_type (sickness/maternity/paternity), benefit calculation fields
- `hr_pension_entitlements` — employee_id FK, ss_record_id FK, pension_type, contribution months, monthly_pension, early pension reduction
- `hr_work_injury_records` — employee_id FK, incident details, disability assessment, perm_disability_pension
- `hr_unemployment_benefits` — employee_id FK, separation details, monthly_benefit, max_benefit_weeks
- `hr_death_survivor_benefits` — deceased_employee_id FK, beneficiaries_json (JSONB)
- `hr_medical_coverages` — employee_id FK, coverage_type (CNAM/AMO/HIO), dependents_json

### Time & Attendance (with Geofencing)
- `hr_time_clock_events` — employee_id FK, event_type (clock_in/out/break), lat/lng, geofence_id FK, is_within_geofence, verification_method (pin/biometric/photo)
- `hr_geofences` — lat/lng, radius_meters, polygon_json (JSONB), allow_clock_outside

### Extended HR (erpStarz Legacy Migration)
- `hr_employee_contracts` — contract_type (CDI/CDD/interim), weekly_hours, trial_period
- `hr_employee_bank_accounts` — RIB, IBAN, BIC/SWIFT
- `hr_employee_salaries` — payroll_month/year, base_salary, overtime, bonuses, gross/net, cnss_employee/employer, income_tax
- `hr_employee_absences` — absence_type, is_excused, reviewed_by_id FK → users
- `hr_employee_suspensions` — suspension_type, hr_case_id FK
- `hr_employee_advances` — amount, installments, monthly_deduction, remaining_balance
- `hr_employee_diplomas` — institution, verified_by_id FK → users
- `hr_employee_addresses` — address_type (home/mailing/emergency)
- `hr_employee_permissions` — short-term leave permits, approved_by_id FK → users
- `hr_employee_documents` — document_type, file_url, is_confidential — **RBAC**
- `hr_employee_histories` — event_type (hire/promotion/transfer), previous/new_value
- `hr_employee_notes` — note_type, is_confidential, visible_to_employee — **RBAC**
- `hr_public_holidays` — jurisdiction, holiday_type
- `hr_leave_balances` — leave_type, year, initial_balance, accrued, used, pending, carried_over
- `hr_cases` — case_type (disciplinary/grievance/harassment), is_confidential — **RBAC**

---

## 26. Training & Skills

**File**: `training.py`

### `skills` (Int PK)
| name, code (unique), skill_category (Enum), proficiency_levels (JSONB: 5 levels), is_safety/quality_critical, requires_recertification, recertification_interval_days, initial/recertification_hours | |

### `skill_requirements` (Int PK)
| skill_id FK, station_id FK, product_id FK, minimum_proficiency_level, is_mandatory | Links skills to stations/products |

### `trainings` (Int PK)
| skill_id FK, training_type (Enum), trainer_id FK → users, provides_certification, cost_per_person, syllabus (JSONB) | |

### `training_participants` (Int PK)
| training_id FK, user_id FK → users, enrollment_status, attendance_status, score, passed, certificate_number | |

### `user_skills` (Int PK)
| user_id FK → users, skill_id FK, proficiency_level, certification_status (Enum), certified_by_id FK → users, expiration_date, assessment_scores (JSONB) | |

### `lessons` (Int PK)
| title, tags (JSONB), target_roles (JSONB) — **RBAC**, skills_taught (JSONB), is_mandatory, compliance_required, difficulty, skill_id FK | ML recommendation system |

### `lesson_completions` (Int PK)
| user_id FK → users, lesson_id FK, completed, rating (1-5), progress_percent, time_spent_minutes | ML collaborative filtering |

---

## 27. Learning System

**File**: `learning.py`

### `learning_modules`
| code, title, category (Enum: TPS/LEAN/QUALITY/etc.), difficulty, learning_objectives (JSONB), prerequisites (JSONB), is_published | |

### `learning_units`
| module_id FK, code, category, content_type, content/content_rich (JSONB), media URLs, key_points/examples/anti_patterns (JSONB), japanese_term, pronunciation | TPS/Lean terminology |

### `user_learning_progress`
| user_id FK → users, module/unit tracking | |

### `learning_assessments`

---

## 28. Analytics & KPIs

**Files**: `analytics.py`, `kpi.py`

### Analytics Data Warehouse
- `daily_snapshots` — snapshot_date, status, record_count — **Analytics**
- `analytics_dimension_schemas` — dim_type, key_column, attribute_columns (JSON)
- `analytics_fact_schemas` — fact_type, dimension_keys (JSON), measure_columns (JSON)
- `analytics_exported_records` — snapshot_id FK, fact_type, data (JSON) — **Analytics**

### KPI Engine
- `kpi_definitions` — name, category (Enum: QUALITY/DELIVERY/COST/SAFETY/PEOPLE/EFFICIENCY/FINANCIAL/OPERATIONAL/CUSTOMER), unit, direction (higher_better/lower_better/target), formula, component_kpis (JSONB), threshold fields, custom_calculator, owner_role — **RBAC & Analytics**
- `kpi_values` — kpi_id FK, value, recorded_at, status, dimensions (JSONB) — **Analytics**
- `kpi_dashboards` — kpi_ids (JSONB), layout (JSONB), owner_id, is_public — **Analytics & RBAC**

---

## 29. AI/ML Models

**File**: `strategic_v2.py`

### Inspection AI
- `ai_inspection_feedback` — operator/ai_decision, is_correct, operator_id FK → users — **AI: feedback loop**
- `ai_training_samples` — sample_type, label_data (JSONB), confidence_score — **AI: training data**

### RFQ Agent AI
- `ai_agent_analyses` — rfq_id FK → rfqs, agent_type, analysis_category, confidence, findings/recommendations (JSONB) — **AI**
- `ai_agent_debates` — rfq_id FK, rounds, outcome, final_consensus_score, debate_log (JSONB) — **AI: multi-agent consensus**

### Knowledge Base AI
- `ai_knowledge_sources` — source_type, uri, metadata_fields (JSONB) — **AI**
- `ai_knowledge_chunks` — source_id FK, content, embedding_id — **AI**
- `ai_knowledge_packs` — name, created_by_id FK → users — **AI**
- `ai_knowledge_pack_sources` — M2M pack↔source — **AI**

### Factory Maturity AI
- `factory_site_maturity` — site_id, current/target_level, deployment_metadata (JSONB) — **AI**
- `factory_level_up_checklists` — site_id FK, from/to_level, items (JSONB) — **AI**

### Lesson Delivery AI
- `ai_lesson_deliveries` — lesson_id, recipient_id FK → users, trigger_type/context (JSONB), feedback_score — **AI**

### Standard Work Evolution AI
- `ai_standard_work_evolution` — suggested_changes (JSONB), reasoning, performance_gain_pct — **AI**

### UI Audit
- `ui_action_audits` — user_id FK → users, action_type, entity_type/id, ui_context (JSONB), duration_ms

---

## 30. Cognitive Obeya (AI)

**File**: `cognitive_obeya.py`

- `obeya_metrics` (Int PK) — metric_id, category (Enum: SAFETY/QUALITY/DELIVERY/COST/PEOPLE/MORALE), name, value, target, status — **Analytics & AI**
- `obeya_causal_links` — source_type/id, confidence, impact_value, explanation — **AI: causal inference**
- `obeya_trend_warnings` — predicted_status, days_to_breach, trend_values (JSONB), recommendation — **AI: predictive**
- `obeya_silo_alerts` — source/affected_department (Enum: ENGINEERING/PRODUCTION/QUALITY/LOGISTICS/etc.), severity — **AI**
- `obeya_rebalance_suggestions` — source/target_work_center, operator_ids (JSONB), skill_match_score — **AI**
- `obeya_heijunka_suggestions` — current/suggested_mix (JSONB), mura_reduction — **AI: production leveling**

---

## 31. Strategic Analytics (AI)

**File**: `strategic.py`

- `strategic_nl2sql_queries` — natural_language, generated_sql, tables_used (JSONB), security_level (Enum), executed_by_id FK — **AI: NL→SQL**
- `strategic_employee_risks` (Int PK) — employee_id, risk_type (Enum: FLIGHT_RISK/BURNOUT/SKILL_GAP/RETIREMENT/PERFORMANCE), risk_score, evidence (JSONB), mitigation_plan — **AI & Analytics**
- `strategic_scenario_results` — scenario_name, parameters/kpi_impacts (JSONB), confidence_score, recommendation — **AI: what-if**
- `strategic_variance_alerts` (UUID PK) — quote_id, actual/estimated_cogs, deviation_pct, severity, work_order_ids (JSONB) — **Analytics**

---

## 32. TPS Gamification

**File**: `tps.py` (all String PK)

- `tps_pdca_cycles` — phase (plan/do/check/act), linked_entity_type/id
- `tps_kata_sessions` — learner_id, coach_id, target_condition, current_condition
- `tps_muda_detections` — muda_type (overproduction/waiting/transport/processing/inventory/motion/defects/talent), estimated_cost
- `tps_andon_events` — category, zone, escalation_level
- `tps_jidoka_responses` — trigger_type, automated_action
- `tps_user_stats` (user_id PK) — xp (Integer), achievements (JSONB), belt_level (String) — **Gamification**

---

## 33. Admin & Configuration

**File**: `admin.py` (all String PK)

- `admin_gates` — phase, required_approvers, bypass_roles (JSONB) — **RBAC**
- `approval_workflows` — type, threshold_amount, required_roles (JSONB), sequence_required, auto_escalate, escalation_roles (JSONB) — **RBAC**
- `templates` — type, content, sections/variables (JSONB)
- `learning_cadences` — frequency, mandatory, target_roles (JSONB) — **RBAC**
- `feature_flags` — key, enabled, rollout_percentage, target_roles (JSONB), category — **RBAC**

---

## 34. Attachments & Audit Trail

**File**: `attachment.py`

### `attachments`
| entity_type/entity_id (polymorphic), filename, mime_type, file_size, storage_bucket/key, category, uploaded_by_id FK → users, is_confidential, access_level — **RBAC**, scan_status, checksums | |

### `attachment_versions`

**File**: `audit_log.py`

### `audit_logs` — **PARTITIONED by RANGE on created_at**
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| created_at | DateTime PK | partition key |
| entity_type, entity_id | String | |
| action | Enum(AuditAction) | create/update/delete/status_change/login/logout/export/import/approve/reject |
| user_id | FK → users | |
| old_values, new_values, changed_fields | JSONB | |
| ip_address, user_agent, request_id | String | |

---

## 35. Data Lineage & AI Reasoning

### `data_lineage_links` (data_lineage.py)
| source_entity_type/id, target_entity_type/id, relationship_type, reasoning_id, link_metadata (JSONB) | UniqueConstraint on all 5 |

### `reasoning_traces` (reasoning_trace.py) 🤖
| entity_type, entity_id, reasoning_id, source | Maps entities to AI reasoning threads |

---

## 36. PII & Privacy

**File**: `pii.py`

- `pii_fields` — table_name, column_name, category, sensitivity, masking_type, retention_days, requires_consent
- `pii_data_subjects` — external_id, subject_type, email, deletion dates
- `pii_consents` — subject_id FK, consent_type, status, purpose
- `pii_access_logs` — subject_id FK, user_id FK → users, field_id FK, access_type, purpose
- `pii_deletion_requests` — subject_id FK, requested_by_id FK → users, affected_tables (JSONB)

---

## 37. Segments & Saved Views

**File**: `segment.py`

- `segments` — name, module (Enum: rfq/quote/opportunity/kanban/andon/a3/etc.), owner_id FK → users, visibility (private/team/department/organization) — **RBAC**, filter_groups/columns/sort_config (JSONB), is_default/pinned/smart/system
- `segment_shares` — segment_id FK, shared_by_id/shared_with_id FK → users, can_edit — **RBAC**
- `segment_usage` — segment_id FK, user_id FK → users, result_count, execution_time_ms — **Analytics**

---

## 38. Service Persistence

**File**: `service_persistence.py`

### Saved Views & Drafts
- `saved_views` — entity_type, owner_id FK → users, visibility, conditions/sort/columns (JSONB) — **RBAC**
- `autosave_drafts` — user_id FK → users, entity_type/id, content (JSONB), expires_at
- `autosave_draft_versions` — draft_id FK, content (JSONB)

### Support Inbox
- `support_tickets` — reporter_id/assignee_id FK → users, category, status, priority, SLA tracking, escalation_level — **RBAC**
- `support_ticket_comments` — ticket_id FK, author_id FK → users, is_internal — **RBAC**
- `user_feedback` — user_id FK → users, feedback_type, rating

### Routing & Escalation
- `support_routing_rules` — conditions (JSONB), target
- `a3_lite_records` — source_ticket_id FK, owner_id FK → users, PDCA fields
- `escalation_policies` — target_type, conditions/escalation_levels (JSONB), notification_channels — **RBAC**
- `escalation_thresholds` — entity_type, threshold_key, value

### Collaboration
- `mentions` — mentioned_user_id FK → users, created_by_id FK → users, source_type/id (polymorphic)
- `entity_assignments` — entity_type/id (polymorphic), assignee_id FK → users, role (owner/reviewer/collaborator) — **RBAC**
- `tasks_from_comments` — task_id FK → tasks, source_comment_id, assignee_id FK → users

### Smart Ingestion
- `smart_ingestion_jobs` — job_type (email/document/file), extracted_entities (JSONB), user_id FK → users — **AI**
- `smart_ingestion_documents` — job_id FK, extracted_text, extracted_fields (JSONB) — **AI**
- `email_drafts` — AI-generated email drafts — **AI**

---

## 39. Knowledge Packs

**File**: `knowledge_pack.py`

### `knowledge_documents`
| title, author, source_url, license_type (Enum), attribution_text, raw/normalized_content, tags (ARRAY), content_hash (unique) | **AI** |

### `knowledge_chunks` 🤖
| document_id FK, chunk_text, chunk_index, heading, section_path (ARRAY), quality_score, tags (ARRAY), **embedding Vector(384)**, citation | **AI: pgvector semantic search** |

### `ingestion_logs`
| source_url, operation, status, document_id FK, chunks_created | |

---

## 40. OT Network Security

**File**: `ot_network.py`

- `network_zones` — name, zone_type (it/ot/dmz), cidrs (ARRAY), is_active
- `zone_violations` — source/dest_zone_id FK, source/dest_ip, severity, acknowledged_by_id FK → users — **RBAC**
- `edge_certificates` — controller_id (unique), subject_cn, issuer, not_before/after, status, fingerprint_sha256

---

## 41. Business Continuity / DR

**File**: `business_continuity.py`

- `queued_events` — device_id, entity_type/id, operation, payload (JSON), status (offline sync)
- `dr_criticality_rules` — entity_type (unique), resolution_strategy
- `dr_rto_rpo_configs` — rto/rpo_minutes, validation_passed
- `dr_restore_rehearsals` — rto/rpo_achieved_minutes

---

## 42. Data Migration

**File**: `migration.py`

- `import_batches` — entity_type, source_file, total/valid/error_records, imported_by, error_log (JSON)

---

## 43. Sites

**File**: `site.py`

- `sites` — site_code (unique), name, status, timezone, country, default_currency, metadata_json (JSONB)

---

## 44. Exceptions

**File**: `exception.py` (String PK)

- `exception_items` — title, category, severity, status, source, owner_id/name, department, source_entity fields, resolution_time_minutes, escalation fields, tags (JSONB), metadata_json (JSONB)

---

## 45. Cross-Model Relationship Diagram

### Core Entity Flow (Quote-to-Cash)
```
Account ──→ Opportunity ──→ RFQ ──→ Qualification
   │              │           │         │
   │              │           ├──→ CTQ  │
   │              │           │         │
   │              └───────→ Quote ──→ Sales Order ──→ Work Order ──→ Production
   │                          │           │              │              │
   │                          │           │              ├──→ Operations │
   │                          │           │              │              │
   └──────────────────────────┘           └──→ Invoice   └──→ Shipment
```

### Manufacturing Execution
```
Work Order ──→ Work Order Operations ──→ Station ──→ Work Center
     │              │                       │           │
     │              └──→ Operator (User)    │           │
     │                                      │           │
     ├──→ Kanban Card                       ├──→ Andon Events
     ├──→ Quality (NC, Inspection)          ├──→ Standard Work
     └──→ Product ──→ BOM Items             └──→ Production Cell
                   └──→ Routings
```

### RBAC Architecture
```
User ──→ UserRole ──→ Role (24 types, hierarchy_level)
                        │
                        └──→ RolePermission ──→ Permission (resource:action)
                                    │
                                    └──→ conditions (JSONB, conditional)

AdminGate.bypass_roles, ApprovalWorkflow.required_roles,
FeatureFlag.target_roles, LearningCadence.target_roles (all JSONB)
```

### AI/ML Architecture
```
RFQ.embedding ──────┐
Quote.embedding ─────┤──→ pgvector Vector(384) ──→ Semantic Search
KnowledgeChunk.embedding ┘

AI Agent Pipeline:
  RFQ ──→ AgentAnalysis ──→ ConsensusDebate ──→ Recommendation
                                                     │
  KnowledgeSource ──→ SemanticChunk ──→ KnowledgePack ┘

InspectionFeedback ──→ TrainingSample ──→ ONNX Model (cbm_predictor, sensei-mfg-onnx)

ReasoningTrace ──→ DataLineageLink ──→ Cross-entity AI provenance
```

### Key Foreign Key Summary

| From Table | FK Column | To Table |
|-----------|-----------|----------|
| All AuditMixin models | created_by_id, updated_by_id, owner_id | users |
| opportunities | account_id, competitor_id, partner_id | accounts |
| rfqs | account_id, opportunity_id, assigned_to_id | accounts, opportunities, users |
| quotes | rfq_id, opportunity_id, account_id, approved_by_id | rfqs, opportunities, accounts, users |
| work_orders | quote_id, sales_order_id, rfq_id, account_id, product_id | quotes, sales_orders, rfqs, accounts, products |
| work_order_operations | work_order_id, station_id, operator_id | work_orders, stations, users |
| non_conformances | product_id, work_order_id, station_id, capa_id, supplier_id | products, work_orders, stations, capas, accounts |
| andon_events | station_id, work_order_id, reported/ack/resolved_by_id | stations, work_orders, users |
| kanban_cards | board_id, work_order_id, product_id, assigned_to_id | kanban_boards, work_orders, products, users |
| hr_employees | user_id, manager_id | users, hr_employees (self) |
| maintenance_assets | work_center_id, station_id, parent_asset_id | work_centers, stations, self |
| sales_orders | account_id, source_quote_id | accounts, quotes |
| purchase_orders | supplier_id, source_pr_id | accounts, purchase_requisitions |

---

## Summary Statistics

| Category | Table Count |
|----------|------------|
| Auth & RBAC | 6 |
| CRM (Accounts/Contacts) | 3 |
| Sales Pipeline (Opp/RFQ/Quote) | ~15 |
| Qualification & CTQ | 5 |
| Risk | 2 |
| Project Management | ~14 |
| Obeya & A3 | 4 |
| Tasks & Notifications | 3 |
| Products/BOM/Routing | 3 |
| Work Centers/Stations | 2 |
| Work Orders | 2 |
| Production | 4 |
| Kanban | 4 |
| Andon | 3 |
| Standard Work | 2 |
| Quality (NC/CAPA) | ~5 |
| Quality QMS | 34 |
| Maintenance | ~15 |
| Inventory/WMS | 10 |
| MRP/MPS | 6 |
| Finance/GL | ~14 |
| Accounts Payable | 11 |
| Accounts Receivable/Shipping | 10 |
| HR & Benefits | 33 |
| Training & Skills | 7 |
| Learning | 4 |
| Analytics & KPIs | 6 |
| AI/ML | ~12 |
| Cognitive Obeya (AI) | 6 |
| Strategic Analytics | 4 |
| TPS Gamification | 6 |
| Admin/Config | 5 |
| Attachments/Audit | 3 |
| Data Lineage/Reasoning | 2 |
| PII/Privacy | 5 |
| Segments/Views | 3 |
| Service Persistence | 16 |
| Knowledge Packs | 3 |
| OT Network | 3 |
| Business Continuity | 4 |
| Migration | 1 |
| Sites | 1 |
| Exceptions | 1 |
| **TOTAL** | **~200+** |

### Special PostgreSQL Features Used
- **pgvector**: `Vector(384)` on `rfqs.embedding`, `quotes.embedding`, `knowledge_chunks.embedding`
- **Partitioning**: `audit_logs` and `condition_readings` use `postgresql_partition_by: RANGE`
- **JSONB**: Extensively used for flexible schemas (60+ columns across models)
- **GIN indexes**: On JSONB and ARRAY columns for fast containment queries
- **IVFFlat index**: On knowledge_chunks.embedding for approximate nearest neighbor search
