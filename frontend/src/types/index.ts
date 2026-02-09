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
  roles: UserRole[];
  /** Backend superuser flag (treated as admin access in the UI). */
  is_superuser?: boolean;
  department?: string;
  job_title?: string;
  phone?: string;
  timezone?: string;
  locale?: string;
  is_active: boolean;
  last_login_at?: string;
  preferences?: UserPreferences;
}

export type UserRole = 
  | 'admin'
  | 'ceo'
  | 'gm'
  | 'exec'
  | 'finance'
  | 'accountant'
  | 'hr'
  | 'ops'
  | 'quality'
  | 'auditor'
  | 'it'
  | 'supervisor'
  | 'team_lead'
  | 'operator'
  | 'viewer'
  | 'sales_engineer'
  | 'estimator'
  | 'supply_chain'
  | 'maintenance'
  | 'warehouse'
  | 'sales'
  | 'purchasing'
  | 'logistics'
  | 'engineering';

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
  revision: number;
  quotes?: Quote[];
  triage_risk_score?: number;
  custom_fields?: Record<string, unknown>;
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
  product?: Product;
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
  | 'incoming'
  | 'in_process'
  | 'final'
  | 'patrol'
  | 'first_article'
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
  | 'under_investigation'
  | 'pending_disposition'
  | 'dispositioned'
  | 'closed'
  | 'escalated_to_capa';

export type Severity = 'minor' | 'major' | 'critical';

export type NCRDisposition = 
  | 'use_as_is'
  | 'rework'
  | 'repair'
  | 'scrap'
  | 'return_to_supplier'
  | 'concession'
  | 'sort'
  | 'downgrade';

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
  | 'investigating'
  | 'implementing'
  | 'verification'
  | 'verifying'
  | 'effectiveness_check'
  | 'effective'
  | 'closed'
  | 'ineffective'
  | 'on_hold';

export type MSAStudyType = 'grr' | 'bias' | 'linearity' | 'stability';

export type MSAStudyStatus = 'in_progress' | 'completed' | 'cancelled';

export interface MSAResult extends AuditableEntity {
  study_id: UUID;
  repeatability_ev: number;
  reproducibility_av: number;
  grr: number;
  part_variation_pv: number;
  total_variation_tv: number;
  grr_percent: number;
  ndc: number;
}

export interface MSAMeasurement extends AuditableEntity {
  study_id: UUID;
  operator_id: UUID;
  operator?: User;
  part_id: string;
  trial_number: number;
  measured_value: number;
  measured_at: string;
}

export interface MSAStudy extends AuditableEntity {
  gauge_id: UUID;
  name: string;
  study_type: MSAStudyType;
  status: MSAStudyStatus;
  parts_count: number;
  operators_count: number;
  trials_count: number;
  started_at: string;
  completed_at?: string;
  notes?: string;
  measurements?: MSAMeasurement[];
  result?: MSAResult;
}

export type ProcessCapabilityStatus = 'in_progress' | 'completed' | 'cancelled';

export interface ProcessCapabilityResult extends AuditableEntity {
  study_id: UUID;
  mean: number;
  std_dev: number;
  cp: number;
  cpk: number;
  cpu: number;
  cpl: number;
  sample_size: number;
}

export interface ProcessCapabilityMeasurement extends AuditableEntity {
  study_id: UUID;
  sample_label?: string;
  measured_value: number;
  measured_at: string;
}

export interface ProcessCapabilityStudy extends AuditableEntity {
  name: string;
  process_name: string;
  characteristic: string;
  status: ProcessCapabilityStatus;
  lsl: number;
  usl: number;
  target?: number;
  unit?: string;
  started_at: string;
  completed_at?: string;
  notes?: string;
  measurements?: ProcessCapabilityMeasurement[];
  result?: ProcessCapabilityResult;
}

export interface CustomerComplaint extends AuditableEntity {
  customer_id?: UUID;
  title: string;
  description: string;
  received_at: string;
  status: string;
  lot_id?: string;
  related_nc_id?: number;
  related_capa_id?: number;
  rma_number?: string;
  root_cause?: string;
  containment_actions?: string[];
  corrective_actions?: string[];
  closed_at?: string;
}

export interface CustomerSurveyResponse extends AuditableEntity {
  survey_id: UUID;
  customer_id?: UUID;
  respondent_name?: string;
  respondent_email?: string;
  nps_score: number;
  comment?: string;
  submitted_at: string;
}

export interface CustomerSurvey extends AuditableEntity {
  title: string;
  description?: string;
  status: string;
  period_start?: string;
  period_end?: string;
  target_responses?: number;
  notes?: string;
  responses?: CustomerSurveyResponse[];
}

export interface CustomerSatisfactionStats {
  nps: {
    total_responses: number;
    promoters: number;
    passives: number;
    detractors: number;
    nps_score: number;
    average_score: number;
  };
  complaints: {
    total: number;
    open: number;
    closed: number;
  };
}

export type FAIStatus = 'in_progress' | 'completed' | 'cancelled';

export interface FAICharacteristic extends AuditableEntity {
  inspection_id: UUID;
  characteristic_number: number;
  requirement: string;
  nominal?: number;
  tolerance?: string;
  actual?: number;
  result: string;
  method?: string;
  tool_id?: UUID;
  notes?: string;
}

export interface FAIInspection extends AuditableEntity {
  inspection_number: string;
  product_id?: UUID;
  work_order_id?: UUID;
  part_number: string;
  revision?: string;
  drawing_number?: string;
  status: FAIStatus;
  inspector_id?: UUID;
  started_at: string;
  completed_at?: string;
  notes?: string;
  characteristics?: FAICharacteristic[];
}

export type SelfInspectionStatus = 'in_progress' | 'completed' | 'cancelled';

export interface SelfInspectionCheck extends AuditableEntity {
  inspection_id: UUID;
  characteristic: string;
  specification?: string;
  actual_value?: string;
  result: string;
  notes?: string;
}

export interface SelfInspection extends AuditableEntity {
  inspection_number: string;
  work_order_id?: UUID;
  product_id?: UUID;
  operator_id: UUID;
  status: SelfInspectionStatus;
  started_at: string;
  completed_at?: string;
  notes?: string;
  checks?: SelfInspectionCheck[];
}

export interface LabTestMethod extends AuditableEntity {
  name: string;
  standard?: string;
  description?: string;
  unit?: string;
  lower_spec?: number;
  upper_spec?: number;
  target_value?: number;
  status: string;
}

export interface LabSample extends AuditableEntity {
  sample_number: string;
  product_id?: UUID;
  work_order_id?: UUID;
  lot_number?: string;
  collected_at: string;
  collected_by_id?: UUID;
  notes?: string;
}

export interface LabTestRun extends AuditableEntity {
  sample_id: UUID;
  method_id: UUID;
  result_value?: number;
  result_text?: string;
  result_status: string;
  tested_at: string;
  tester_id?: UUID;
  notes?: string;
}

export type AQLInspectionResult = 'accept' | 'reject' | 'pending';

export interface AQLSamplingPlan extends AuditableEntity {
  plan_code: string;
  standard: string;
  inspection_level: string;
  aql_level: string;
  lot_size_min: number;
  lot_size_max: number;
  sample_size: number;
  accept_limit: number;
  reject_limit: number;
  status: string;
  notes?: string;
}

export interface AQLLotInspection extends AuditableEntity {
  plan_id: UUID;
  lot_number: string;
  lot_size: number;
  sample_size: number;
  defect_count: number;
  accept_limit: number;
  reject_limit: number;
  result: AQLInspectionResult;
  inspected_at: string;
  inspector_id?: UUID;
  inspection_level: string;
  aql_level: string;
  defects_json?: Array<Record<string, unknown>>;
  notes?: string;
}

export interface TraceabilityMatrix extends AuditableEntity {
  name: string;
  description?: string;
  status: string;
  product_id?: string;
  work_order_id?: number;
  lot_number?: string;
  batch_id?: string;
  external_reference?: string;
  metadata_json?: Record<string, unknown>;
}

export interface TraceabilityLink extends AuditableEntity {
  matrix_id: UUID;
  link_type: string;
  reference_id: string;
  reference_table?: string;
  notes?: string;
  metadata_json?: Record<string, unknown>;
}

export interface ChangePointStudy extends AuditableEntity {
  name: string;
  process_name: string;
  characteristic: string;
  method: string;
  sensitivity?: number;
  status: string;
  started_at: string;
  completed_at?: string;
  notes?: string;
  metadata_json?: Record<string, unknown>;
}

export interface ChangePointObservation extends AuditableEntity {
  study_id: UUID;
  observed_at: string;
  value: number;
  sample_label?: string;
}

export interface ChangePointEvent extends AuditableEntity {
  study_id: UUID;
  detected_at: string;
  index_position: number;
  change_magnitude: number;
  confidence?: number;
  notes?: string;
}

export interface ManagementReview extends AuditableEntity {
  title: string;
  period_start: string;
  period_end: string;
  status: string;
  scheduled_for: string;
  held_at?: string;
  notes?: string;
  attendees?: string[];
  metrics_snapshot?: Record<string, unknown>;
}

export interface ManagementReviewAction extends AuditableEntity {
  review_id: UUID;
  title: string;
  status: string;
  due_date?: string;
  assignee_id?: UUID;
  notes?: string;
}

export interface Site extends AuditableEntity {
  site_code: string;
  name: string;
  status: string;
  timezone?: string;
  country?: string;
  address?: string;
  default_currency?: string;
  metadata_json?: Record<string, unknown>;
}

// ============================================================================
// Finance - Banking & Payments
// ============================================================================

export interface Currency extends AuditableEntity {
  code: string;
  name: string;
  symbol?: string;
  decimal_places: number;
  is_active: boolean;
  legacy_id?: string;
}

export interface PaymentTerm extends AuditableEntity {
  code: string;
  name: string;
  days_due: number;
  discount_percent: number;
  discount_days: number;
  description?: string;
  is_active: boolean;
  legacy_id?: string;
}

export interface BankAccount extends AuditableEntity {
  account_name: string;
  account_number: string;
  bank_name: string;
  bank_code?: string;
  iban?: string;
  currency: string;
  account_type: BankAccountType;
  site_id?: UUID;
  site?: Site;
  gl_account_id?: UUID;
  current_balance: number;
  is_active: boolean;
  legacy_id?: string;
}

export type BankAccountType = 'checking' | 'savings' | 'cash';

export interface BankTransaction extends AuditableEntity {
  bank_account_id: UUID;
  bank_account?: BankAccount;
  transaction_date: string;
  value_date?: string;
  transaction_type: BankTransactionType;
  reference?: string;
  description: string;
  amount: number;
  currency: string;
  running_balance?: number;
  status: BankTransactionStatus;
  reconciled_at?: string;
  reconciled_by_id?: UUID;
  source_type?: string;
  source_id?: UUID;
  legacy_id?: string;
}

export type BankTransactionType = 'deposit' | 'withdrawal' | 'transfer' | 'fee' | 'interest';
export type BankTransactionStatus = 'pending' | 'posted' | 'reconciled' | 'voided';

// ============================================================================
// Shipping & Fulfillment
// ============================================================================

export interface Shipment extends AuditableEntity {
  shipment_number: string;
  sales_order_id?: UUID;
  account_id: UUID;
  account?: Customer;
  ship_from_warehouse_id?: UUID;
  ship_date?: string;
  expected_delivery?: string;
  actual_delivery?: string;
  carrier?: string;
  tracking_number?: string;
  service_level?: ShippingServiceLevel;
  ship_to_name: string;
  ship_to_address: string;
  ship_to_city?: string;
  ship_to_state?: string;
  ship_to_postal?: string;
  ship_to_country: string;
  weight?: number;
  weight_uom?: string;
  status: ShipmentStatus;
  notes?: string;
  legacy_id?: string;
  lines: ShipmentLine[];
}

export type ShipmentStatus = 'pending' | 'picked' | 'packed' | 'shipped' | 'delivered' | 'canceled';
export type ShippingServiceLevel = 'ground' | 'express' | 'overnight';

export interface ShipmentLine extends BaseEntity {
  shipment_id: UUID;
  sales_order_line_id?: UUID;
  sku: string;
  description?: string;
  quantity_shipped: number;
  uom: string;
  lot_number?: string;
  serial_number?: string;
  legacy_id?: string;
}

// ============================================================================
// WMS - Pick Lists
// ============================================================================

export interface PickList extends AuditableEntity {
  pick_number: string;
  warehouse_id: UUID;
  source_type: PickListSourceType;
  source_id: UUID;
  assigned_to_id?: UUID;
  assigned_to?: User;
  device_id?: UUID;
  priority: number;
  pick_strategy: PickStrategy;
  status: PickListStatus;
  started_at?: string;
  completed_at?: string;
  notes?: string;
  legacy_id?: string;
  lines: PickListLine[];
}

export type PickListSourceType = 'sales_order' | 'transfer_order' | 'work_order';
export type PickStrategy = 'FIFO' | 'FEFO' | 'LIFO';
export type PickListStatus = 'pending' | 'in_progress' | 'completed' | 'canceled';

export interface PickListLine extends BaseEntity {
  pick_list_id: UUID;
  sku: string;
  description?: string;
  source_location_id: UUID;
  target_location_id?: UUID;
  quantity_requested: number;
  quantity_picked: number;
  uom: string;
  lot_number?: string;
  serial_number?: string;
  lpn_id?: UUID;
  status: PickLineStatus;
  picked_at?: string;
  legacy_id?: string;
}

export type PickLineStatus = 'pending' | 'picked' | 'short' | 'skipped';

export interface MPSPlan extends AuditableEntity {
  name: string;
  status: string;
  period_start: string;
  period_end: string;
  horizon_days: number;
  notes?: string;
}

export interface MPSPlanLine extends AuditableEntity {
  plan_id: UUID;
  product_id: string;
  bucket_date: string;
  quantity: number;
  source_type?: string;
}

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

// HR Types
// ============================================================================

export interface EmployeeProfile extends AuditableEntity, SoftDeletableEntity {
  user_id?: UUID;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  department?: string;
  job_title?: string;
  site_id?: string;
  manager_id?: UUID;
  manager?: EmployeeProfile;
  cost_center_code?: string;
  jurisdiction: 'TN' | 'MA' | 'EG' | string;
  status: 'active' | 'onboarding' | 'offboarding' | 'terminated';
  hire_date?: string;
  termination_date?: string;
  user?: any; // Avoiding circular dependency with User for now ideally User type
}

export interface HRChecklist extends AuditableEntity {
  employee_id: UUID;
  checklist_type: 'onboarding' | 'offboarding';
  status: 'not_started' | 'in_progress' | 'completed';
  items_json: any[];
}

export interface HRJobOpening extends AuditableEntity, SoftDeletableEntity {
  title: string;
  description: string;
  department?: string;
  requirements?: string;
  status: 'open' | 'filled' | 'cancelled';
  posted_at: string;
  hiring_manager_id: UUID;
  location?: string;
  employment_type?: 'full_time' | 'part_time' | 'contract' | 'intern';
  salary_range_min?: number;
  salary_range_max?: number;
  applications_count?: number;
}

export interface HRJobApplication extends AuditableEntity {
  job_opening_id: UUID;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  resume_url?: string;
  cover_letter?: string;
  status: 'received' | 'screening' | 'interview' | 'offer' | 'hired' | 'rejected';
  notes?: string;
  rating?: number;
}

export interface HRLeaveRequest extends AuditableEntity {
  employee_id: UUID;
  employee?: EmployeeProfile;
  leave_type: 'pto' | 'sick' | 'personal' | 'bereavement' | 'other';
  start_date: string;
  end_date: string;
  status: 'pending' | 'approved' | 'rejected';
  approved_by_id?: UUID;
  reason?: string;
  days_count?: number;
}

