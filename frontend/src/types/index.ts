// ============================================================================
// Core Types
// ============================================================================

export type UUID = string;

export type Status = 'active' | 'inactive' | 'pending' | 'completed' | 'failed' | 'cancelled';

export interface BaseEntity {
  id: UUID;
  created_at: string;
  updated_at: string;
}

export interface AuditableEntity extends BaseEntity {
  created_by: UUID;
  updated_by: UUID;
}

export interface SoftDeletableEntity extends BaseEntity {
  deleted_at: string | null;
  deleted_by: UUID | null;
}

// ============================================================================
// User & Auth Types
// ============================================================================

export interface User extends BaseEntity {
  email: string;
  full_name: string;
  avatar_url?: string;
  role: UserRole;
  department?: string;
  job_title?: string;
  phone?: string;
  timezone: string;
  locale: string;
  is_active: boolean;
  last_login_at?: string;
  preferences: UserPreferences;
}

export type UserRole = 
  | 'admin'
  | 'manager'
  | 'engineer'
  | 'quality_tech'
  | 'production_lead'
  | 'sales_rep'
  | 'viewer';

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  notifications_enabled: boolean;
  email_digest: 'daily' | 'weekly' | 'none';
  default_view: 'list' | 'kanban' | 'calendar';
  sidebar_collapsed: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
}

// ============================================================================
// RFQ & Quote Types
// ============================================================================

export interface RFQ extends AuditableEntity {
  rfq_number: string;
  customer_id: UUID;
  customer: Customer;
  title: string;
  description?: string;
  status: RFQStatus;
  priority: Priority;
  due_date: string;
  received_date: string;
  estimated_value?: number;
  currency: string;
  notes?: string;
  attachments: Attachment[];
  line_items: RFQLineItem[];
  assigned_to?: UUID;
  assigned_user?: User;
  tags: string[];
}

export type RFQStatus = 
  | 'new'
  | 'reviewing'
  | 'quoting'
  | 'submitted'
  | 'won'
  | 'lost'
  | 'no_bid'
  | 'cancelled';

export type Priority = 'low' | 'medium' | 'high' | 'urgent';

export interface RFQLineItem extends BaseEntity {
  rfq_id: UUID;
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  target_price?: number;
  notes?: string;
  specifications?: Record<string, unknown>;
}

export interface Quote extends AuditableEntity {
  quote_number: string;
  rfq_id: UUID;
  rfq: RFQ;
  version: number;
  status: QuoteStatus;
  valid_until: string;
  total_amount: number;
  currency: string;
  discount_percentage?: number;
  discount_amount?: number;
  tax_amount?: number;
  terms_and_conditions?: string;
  notes?: string;
  line_items: QuoteLineItem[];
  approval_status: ApprovalStatus;
  approved_by?: UUID;
  approved_at?: string;
}

export type QuoteStatus = 
  | 'draft'
  | 'pending_approval'
  | 'approved'
  | 'sent'
  | 'accepted'
  | 'rejected'
  | 'expired';

export type ApprovalStatus = 
  | 'not_required'
  | 'pending'
  | 'approved'
  | 'rejected';

export interface QuoteLineItem extends BaseEntity {
  quote_id: UUID;
  rfq_line_item_id?: UUID;
  part_number: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  unit_price: number;
  extended_price: number;
  cost?: number;
  margin?: number;
  lead_time_days?: number;
  notes?: string;
}

// ============================================================================
// Customer Types
// ============================================================================

export interface Customer extends BaseEntity {
  name: string;
  code: string;
  type: CustomerType;
  status: Status;
  industry?: string;
  website?: string;
  phone?: string;
  email?: string;
  address?: Address;
  billing_address?: Address;
  shipping_address?: Address;
  primary_contact_id?: UUID;
  primary_contact?: Contact;
  tax_id?: string;
  payment_terms?: string;
  credit_limit?: number;
  notes?: string;
  tags: string[];
}

export type CustomerType = 'prospect' | 'customer' | 'former_customer';

export interface Contact extends BaseEntity {
  customer_id: UUID;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  mobile?: string;
  job_title?: string;
  department?: string;
  is_primary: boolean;
  is_active: boolean;
  notes?: string;
}

export interface Address {
  street1: string;
  street2?: string;
  city: string;
  state?: string;
  postal_code: string;
  country: string;
}

// ============================================================================
// Product Types
// ============================================================================

export interface Product extends AuditableEntity {
  part_number: string;
  name: string;
  description?: string;
  category_id?: UUID;
  category?: ProductCategory;
  status: ProductStatus;
  unit_of_measure: string;
  weight?: number;
  weight_unit?: string;
  dimensions?: ProductDimensions;
  cost?: number;
  list_price?: number;
  lead_time_days?: number;
  minimum_order_quantity?: number;
  specifications?: Record<string, unknown>;
  images: ProductImage[];
  documents: Attachment[];
  bom?: BOMItem[];
  revision: string;
  is_active: boolean;
}

export type ProductStatus = 
  | 'active'
  | 'inactive'
  | 'discontinued'
  | 'pending_approval'
  | 'prototype';

export interface ProductCategory extends BaseEntity {
  name: string;
  description?: string;
  parent_id?: UUID;
  parent?: ProductCategory;
  children?: ProductCategory[];
  path: string;
}

export interface ProductDimensions {
  length: number;
  width: number;
  height: number;
  unit: string;
}

export interface ProductImage extends BaseEntity {
  product_id: UUID;
  url: string;
  thumbnail_url: string;
  alt_text?: string;
  is_primary: boolean;
  sort_order: number;
}

export interface BOMItem extends BaseEntity {
  parent_product_id: UUID;
  child_product_id: UUID;
  child_product?: Product;
  quantity: number;
  unit_of_measure: string;
  reference_designator?: string;
  notes?: string;
  sort_order: number;
}

// ============================================================================
// Work Order Types
// ============================================================================

export interface WorkOrder extends AuditableEntity {
  work_order_number: string;
  product_id: UUID;
  product: Product;
  quantity: number;
  quantity_completed: number;
  quantity_scrapped: number;
  status: WorkOrderStatus;
  priority: Priority;
  scheduled_start: string;
  scheduled_end: string;
  actual_start?: string;
  actual_end?: string;
  work_center_id?: UUID;
  work_center?: WorkCenter;
  assigned_to?: UUID;
  assigned_user?: User;
  notes?: string;
  operations: WorkOrderOperation[];
}

export type WorkOrderStatus = 
  | 'planned'
  | 'released'
  | 'in_progress'
  | 'on_hold'
  | 'completed'
  | 'cancelled';

export interface WorkOrderOperation extends BaseEntity {
  work_order_id: UUID;
  sequence: number;
  name: string;
  description?: string;
  work_center_id?: UUID;
  work_center?: WorkCenter;
  setup_time_minutes?: number;
  run_time_minutes?: number;
  status: OperationStatus;
  started_at?: string;
  completed_at?: string;
  notes?: string;
}

export type OperationStatus = 
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'skipped';

export interface WorkCenter extends BaseEntity {
  name: string;
  code: string;
  description?: string;
  type: WorkCenterType;
  capacity: number;
  capacity_unit: string;
  efficiency_percentage: number;
  cost_per_hour?: number;
  is_active: boolean;
}

export type WorkCenterType = 
  | 'machine'
  | 'assembly'
  | 'inspection'
  | 'packaging'
  | 'other';

// ============================================================================
// Quality Types
// ============================================================================

export interface QualityInspection extends AuditableEntity {
  inspection_number: string;
  work_order_id?: UUID;
  work_order?: WorkOrder;
  product_id: UUID;
  product: Product;
  type: InspectionType;
  status: InspectionStatus;
  inspector_id: UUID;
  inspector: User;
  inspection_date: string;
  quantity_inspected: number;
  quantity_passed: number;
  quantity_failed: number;
  notes?: string;
  results: InspectionResult[];
  ncrs: NonConformanceReport[];
}

export type InspectionType = 
  | 'receiving'
  | 'in_process'
  | 'final'
  | 'audit';

export type InspectionStatus = 
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export interface InspectionResult extends BaseEntity {
  inspection_id: UUID;
  characteristic: string;
  specification: string;
  actual_value: string;
  is_pass: boolean;
  notes?: string;
}

export interface NonConformanceReport extends AuditableEntity {
  ncr_number: string;
  inspection_id?: UUID;
  work_order_id?: UUID;
  product_id: UUID;
  product: Product;
  status: NCRStatus;
  severity: Severity;
  description: string;
  root_cause?: string;
  disposition?: NCRDisposition;
  quantity_affected: number;
  cost_impact?: number;
  assigned_to?: UUID;
  assigned_user?: User;
  due_date?: string;
  closed_at?: string;
  attachments: Attachment[];
  capa?: CAPA;
}

export type NCRStatus = 
  | 'open'
  | 'investigating'
  | 'pending_disposition'
  | 'closed';

export type Severity = 'minor' | 'major' | 'critical';

export type NCRDisposition = 
  | 'use_as_is'
  | 'rework'
  | 'scrap'
  | 'return_to_vendor'
  | 'concession';

export interface CAPA extends AuditableEntity {
  capa_number: string;
  ncr_id?: UUID;
  type: CAPAType;
  status: CAPAStatus;
  title: string;
  description: string;
  root_cause_analysis?: string;
  corrective_action?: string;
  preventive_action?: string;
  assigned_to: UUID;
  assigned_user: User;
  due_date: string;
  completed_at?: string;
  verified_by?: UUID;
  verified_at?: string;
  effectiveness_review?: string;
  attachments: Attachment[];
}

export type CAPAType = 'corrective' | 'preventive' | 'both';

export type CAPAStatus = 
  | 'open'
  | 'in_progress'
  | 'pending_verification'
  | 'verified'
  | 'closed';

// ============================================================================
// A3 Problem Solving
// ============================================================================

export interface A3Report extends AuditableEntity {
  a3_number: string;
  title: string;
  status: A3Status;
  type: A3Type;
  owner_id: UUID;
  owner: User;
  sponsor_id?: UUID;
  sponsor?: User;
  background: string;
  current_condition: string;
  goal: string;
  root_cause_analysis?: string;
  countermeasures?: string;
  implementation_plan?: string;
  follow_up?: string;
  due_date?: string;
  completed_at?: string;
  linked_ncr_id?: UUID;
  linked_capa_id?: UUID;
  attachments: Attachment[];
  comments: Comment[];
}

export type A3Status = 
  | 'draft'
  | 'in_progress'
  | 'pending_review'
  | 'approved'
  | 'completed'
  | 'cancelled';

export type A3Type = 
  | 'problem_solving'
  | 'proposal'
  | 'status_report';

// ============================================================================
// Obeya / Visual Management
// ============================================================================

export interface ObeyaBoard extends AuditableEntity {
  name: string;
  description?: string;
  type: ObeyaBoardType;
  owner_id: UUID;
  owner: User;
  is_active: boolean;
  layout: ObeyaLayout;
  widgets: ObeyaWidget[];
  members: UUID[];
}

export type ObeyaBoardType = 
  | 'project'
  | 'department'
  | 'value_stream'
  | 'custom';

export interface ObeyaLayout {
  columns: number;
  rows: number;
}

export interface ObeyaWidget extends BaseEntity {
  board_id: UUID;
  type: WidgetType;
  title: string;
  position: WidgetPosition;
  config: Record<string, unknown>;
  data_source?: string;
  refresh_interval_seconds?: number;
}

export type WidgetType = 
  | 'kpi_card'
  | 'chart'
  | 'table'
  | 'timeline'
  | 'kanban'
  | 'checklist'
  | 'text'
  | 'image'
  | 'embedded';

export interface WidgetPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

// ============================================================================
// Tasks & Kanban
// ============================================================================

export interface Task extends AuditableEntity {
  title: string;
  description?: string;
  status: TaskStatus;
  priority: Priority;
  type: TaskType;
  assigned_to?: UUID;
  assigned_user?: User;
  due_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  parent_task_id?: UUID;
  subtasks?: Task[];
  linked_entity_type?: string;
  linked_entity_id?: UUID;
  tags: string[];
  attachments: Attachment[];
  comments: Comment[];
  checklist: ChecklistItem[];
}

export type TaskStatus = 
  | 'backlog'
  | 'todo'
  | 'in_progress'
  | 'in_review'
  | 'done'
  | 'cancelled';

export type TaskType = 
  | 'task'
  | 'bug'
  | 'feature'
  | 'improvement'
  | 'other';

export interface ChecklistItem {
  id: UUID;
  text: string;
  is_completed: boolean;
  completed_at?: string;
  completed_by?: UUID;
}

export interface KanbanBoard extends AuditableEntity {
  name: string;
  description?: string;
  owner_id: UUID;
  owner: User;
  columns: KanbanColumn[];
  members: UUID[];
  is_active: boolean;
}

export interface KanbanColumn extends BaseEntity {
  board_id: UUID;
  name: string;
  task_status: TaskStatus;
  wip_limit?: number;
  sort_order: number;
  color?: string;
}

// ============================================================================
// Common Types
// ============================================================================

export interface Attachment extends BaseEntity {
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  url: string;
  thumbnail_url?: string;
  uploaded_by: UUID;
  uploader?: User;
  entity_type: string;
  entity_id: UUID;
}

export interface Comment extends BaseEntity {
  content: string;
  author_id: UUID;
  author: User;
  entity_type: string;
  entity_id: UUID;
  parent_id?: UUID;
  replies?: Comment[];
  mentions: UUID[];
  edited_at?: string;
  is_resolved?: boolean;
}

export interface AuditLog extends BaseEntity {
  user_id: UUID;
  user: User;
  action: string;
  entity_type: string;
  entity_id: UUID;
  old_values?: Record<string, unknown>;
  new_values?: Record<string, unknown>;
  ip_address?: string;
  user_agent?: string;
}

export interface Notification extends BaseEntity {
  user_id: UUID;
  type: NotificationType;
  title: string;
  message: string;
  link?: string;
  is_read: boolean;
  read_at?: string;
  entity_type?: string;
  entity_id?: UUID;
}

export type NotificationType = 
  | 'info'
  | 'success'
  | 'warning'
  | 'error'
  | 'mention'
  | 'assignment'
  | 'due_date'
  | 'approval';

// ============================================================================
// KPI & Dashboard Types
// ============================================================================

export interface KPI extends BaseEntity {
  name: string;
  description?: string;
  category: KPICategory;
  unit: string;
  target_value?: number;
  warning_threshold?: number;
  critical_threshold?: number;
  trend_direction: 'up_good' | 'down_good' | 'neutral';
  calculation_method?: string;
  data_source?: string;
  is_active: boolean;
}

export type KPICategory = 
  | 'quality'
  | 'delivery'
  | 'cost'
  | 'safety'
  | 'productivity'
  | 'people';

export interface KPIValue extends BaseEntity {
  kpi_id: UUID;
  kpi: KPI;
  value: number;
  period_start: string;
  period_end: string;
  notes?: string;
}

export interface Dashboard extends AuditableEntity {
  name: string;
  description?: string;
  owner_id: UUID;
  owner: User;
  is_default: boolean;
  is_shared: boolean;
  layout: DashboardLayout;
  widgets: DashboardWidget[];
}

export interface DashboardLayout {
  type: 'grid' | 'freeform';
  columns?: number;
}

export interface DashboardWidget extends BaseEntity {
  dashboard_id: UUID;
  type: DashboardWidgetType;
  title: string;
  position: WidgetPosition;
  config: Record<string, unknown>;
  kpi_ids?: UUID[];
  refresh_interval_seconds?: number;
}

export type DashboardWidgetType = 
  | 'kpi_card'
  | 'kpi_trend'
  | 'pie_chart'
  | 'bar_chart'
  | 'line_chart'
  | 'table'
  | 'list'
  | 'calendar'
  | 'activity_feed';

// ============================================================================
// Training & Skills
// ============================================================================

export interface TrainingRecord extends AuditableEntity {
  user_id: UUID;
  user: User;
  course_id: UUID;
  course: TrainingCourse;
  status: TrainingStatus;
  started_at?: string;
  completed_at?: string;
  score?: number;
  passing_score?: number;
  certificate_url?: string;
  expires_at?: string;
  trainer_id?: UUID;
  trainer?: User;
  notes?: string;
}

export type TrainingStatus = 
  | 'not_started'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'expired';

export interface TrainingCourse extends BaseEntity {
  name: string;
  code: string;
  description?: string;
  category: string;
  duration_hours: number;
  is_required: boolean;
  recertification_days?: number;
  content_url?: string;
  is_active: boolean;
}

export interface Skill extends BaseEntity {
  name: string;
  description?: string;
  category: string;
  level: SkillLevel;
  is_active: boolean;
}

export type SkillLevel = 
  | 'beginner'
  | 'intermediate'
  | 'advanced'
  | 'expert';

export interface UserSkill extends BaseEntity {
  user_id: UUID;
  skill_id: UUID;
  skill: Skill;
  level: SkillLevel;
  verified_by?: UUID;
  verified_at?: string;
  expires_at?: string;
}

// ============================================================================
// Standard Work
// ============================================================================

export interface StandardWork extends AuditableEntity {
  document_number: string;
  title: string;
  description?: string;
  version: string;
  status: DocumentStatus;
  type: StandardWorkType;
  work_center_id?: UUID;
  work_center?: WorkCenter;
  product_id?: UUID;
  product?: Product;
  takt_time_seconds?: number;
  cycle_time_seconds?: number;
  steps: StandardWorkStep[];
  attachments: Attachment[];
  approved_by?: UUID;
  approved_at?: string;
  effective_date?: string;
  supersedes_id?: UUID;
}

export type DocumentStatus = 
  | 'draft'
  | 'pending_review'
  | 'approved'
  | 'released'
  | 'obsolete';

export type StandardWorkType = 
  | 'sop'
  | 'work_instruction'
  | 'job_breakdown'
  | 'one_point_lesson';

export interface StandardWorkStep extends BaseEntity {
  standard_work_id: UUID;
  sequence: number;
  title: string;
  description: string;
  key_points?: string;
  reasons?: string;
  time_seconds?: number;
  image_url?: string;
  video_url?: string;
  tools?: string[];
  safety_notes?: string;
}

// ============================================================================
// Risk Management
// ============================================================================

export interface Risk extends AuditableEntity {
  risk_number: string;
  title: string;
  description: string;
  category: RiskCategory;
  status: RiskStatus;
  probability: RiskLevel;
  impact: RiskLevel;
  risk_score: number;
  owner_id: UUID;
  owner: User;
  mitigation_plan?: string;
  contingency_plan?: string;
  due_date?: string;
  reviewed_at?: string;
  linked_entity_type?: string;
  linked_entity_id?: UUID;
  attachments: Attachment[];
}

export type RiskCategory = 
  | 'operational'
  | 'financial'
  | 'technical'
  | 'compliance'
  | 'strategic'
  | 'safety';

export type RiskStatus = 
  | 'identified'
  | 'assessing'
  | 'mitigating'
  | 'monitoring'
  | 'closed';

export type RiskLevel = 1 | 2 | 3 | 4 | 5;

// ============================================================================
// Andon
// ============================================================================

export interface AndonEvent extends AuditableEntity {
  andon_number: string;
  work_center_id: UUID;
  work_center: WorkCenter;
  type: AndonType;
  status: AndonStatus;
  severity: Severity;
  description: string;
  triggered_by: UUID;
  triggered_user: User;
  acknowledged_by?: UUID;
  acknowledged_at?: string;
  resolved_by?: UUID;
  resolved_at?: string;
  root_cause?: string;
  resolution?: string;
  downtime_minutes?: number;
  escalation_level: number;
}

export type AndonType = 
  | 'quality'
  | 'safety'
  | 'material'
  | 'equipment'
  | 'assistance';

export type AndonStatus = 
  | 'triggered'
  | 'acknowledged'
  | 'in_progress'
  | 'resolved'
  | 'escalated';

// ============================================================================
// API Response Types
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ListFilters {
  search?: string;
  status?: string;
  priority?: string;
  assigned_to?: UUID;
  created_after?: string;
  created_before?: string;
  updated_after?: string;
  updated_before?: string;
  tags?: string[];
}

export interface SortOptions {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface QueryParams extends ListFilters, SortOptions {
  page?: number;
  limit?: number;
}
