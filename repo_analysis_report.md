# Repository File-by-File Analysis (Auto-Generated)

## Scope and Exclusions
Excluded directories: .cache, .git, .next, .pytest_cache, .venv, __pycache__, backend/.mypy_cache, backend/.ruff_cache, e2e-screenshots, frontend/.next, frontend/e2e/screenshots, frontend/playwright-report, frontend/test-results, node_modules, playwright-report, role-screenshots, test-results, venv
Excluded extensions: .avi, .data, .exit, .gif, .gz, .ico, .jpeg, .jpg, .log, .mov, .mp3, .mp4, .onnx, .pdf, .png, .pyc, .pyo, .svg, .tar, .wav, .zip
Excluded files: .env

### .github/workflows/backend-ci.yml
- Size: 3016 bytes
- Lines: 126
- Top-level keys (heuristic): name, on, defaults, jobs

### .github/workflows/cd.yml
- Size: 2073 bytes
- Lines: 73
- Top-level keys (heuristic): name, on, jobs

### .github/workflows/frontend-ci.yml
- Size: 2427 bytes
- Lines: 103
- Top-level keys (heuristic): name, on, defaults, jobs

### .gitignore
- Size: 3621 bytes
- Lines: 230
- Snippet: # Byte-compiled / optimized / DLL files

### .idea/.gitignore
- Size: 228 bytes
- Lines: 11
- Snippet: # Default ignored files

### .idea/Management-Software.iml
- Size: 336 bytes
- Lines: 9
- Snippet: <?xml version="1.0" encoding="UTF-8"?>

### .idea/misc.xml
- Size: 232 bytes
- Lines: 5
- Snippet: <project version="4">

### .idea/modules.xml
- Size: 290 bytes
- Lines: 8
- Snippet: <?xml version="1.0" encoding="UTF-8"?>

### .idea/vcs.xml
- Size: 167 bytes
- Lines: 6
- Snippet: <?xml version="1.0" encoding="UTF-8"?>

### .idea/workspace.xml
- Size: 29583 bytes
- Lines: 388
- Snippet: <?xml version="1.0" encoding="UTF-8"?>

### CONTRIBUTING.md
- Size: 13447 bytes
- Lines: 602
- Headings: # Contributing to Starz Morocco Manufacturing Management System | ## 📋 Table of Contents | ## 📜 Code of Conduct | ## 🚀 Getting Started | ### Prerequisites | ### Setup Development Environment | # Start PostgreSQL (Docker) | # Run migrations | # Create admin user | # Create .env.local | # Terminal 1: Start backend | # Terminal 2: Start frontend
- First paragraph: Thank you for your interest in contributing to the Starz Morocco Management Software! This document provides guidelines and instructions for contributing to the project.

### Development_Plan.md
- Size: 235871 bytes
- Lines: 2672
- Headings: # Sensei OS — Development Master Plan | ## Implementation Progress Log | ### Summary Statistics | #### Backend (Complete ✅) | #### Frontend (Complete ✅) | ### Section 1: Technology Stack & Setup — COMPLETE ✅ | ### Section 2: Core Data & CRM — COMPLETE ✅ | ### Section 3: RFQ & Qualification — COMPLETE ✅ | ### Section 4: Quoting & Onboarding — COMPLETE ✅ | ### Section 5: Management & Learning Systems — COMPLETE ✅ | ### Section 7: Production & TPS (Phase 3) — COMPLETE ✅ | ### Section 6: Machine Learning & AI — COMPLETE ✅
- First paragraph: ---

### README.md
- Size: 10030 bytes
- Lines: 318
- Headings: # Starz Morocco Manufacturing Management System | ## ✨ Features | ### Core Functionality | ### Advanced Features | ### Technical Highlights | ## 🚀 Quick Start | ### Prerequisites | ### Local Development | # Clone repository | # Backend setup | # Frontend setup (new terminal) | ### Docker Compose (Development)
- First paragraph: [![Build Status](https://github.com/sbelakho2/Management-Software/workflows/CI/badge.svg)](https://github.com/sbelakho2/Management-Software/actions)

### SECURITY.md
- Size: 8083 bytes
- Lines: 306
- Headings: # Security Policy | ## 🔒 Supported Versions | ## 🐛 Reporting a Vulnerability | ### Reporting Process | ### What to Expect | ### Disclosure Policy | ## 🛡️ Security Features | ### Authentication & Authorization | ### Data Protection | ### API Security | ### Infrastructure Security | ### Application Security
- First paragraph: We release security updates for the following versions:

### backend/.gitignore
- Size: 590 bytes
- Lines: 69
- Snippet: # Python

### backend/Dockerfile
- Size: 1532 bytes
- Lines: 61
- Snippet: FROM python:3.11-slim-bookworm as builder

### backend/README.md
- Size: 949 bytes
- Lines: 46
- Headings: # Starz Morocco Backend | ## Overview | ## Development Setup | ## Project Structure | ## License
- First paragraph: Intelligent Management System for Manufacturing Excellence.

### backend/alembic/env.py
- Size: 3638 bytes
- Lines: 150
- Classes: None
- Functions: run_migrations_offline, do_run_migrations, run_migrations_online

### backend/alembic/script.py.mako
- Size: 635 bytes
- Lines: 27
- Snippet: """${message}

### backend/alembic/versions/.gitkeep
- Size: 29 bytes
- Lines: 2
- Snippet: # Alembic versions directory

### backend/alembic/versions/20260104_175244_16348c26f8db_initial_database_schema.py
- Size: 251316 bytes
- Lines: 5218
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260111_012452_cc096eda932a_add_project_management_system.py
- Size: 36602 bytes
- Lines: 692
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260111_130500_8f3a2c1d4b7a_add_data_lineage_links.py
- Size: 3205 bytes
- Lines: 86
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260111_154500_f1c2a3b4c5d6_add_reasoning_traces.py
- Size: 2206 bytes
- Lines: 56
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260112_130000_partition_audit_and_condition.py
- Size: 6864 bytes
- Lines: 144
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260114_085314_0917bb9fc206_add_project_sequences.py
- Size: 961 bytes
- Lines: 35
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic/versions/20260114_103000_add_subtask_status.py
- Size: 794 bytes
- Lines: 30
- Classes: None
- Functions: upgrade, downgrade

### backend/alembic.ini
- Size: 2474 bytes
- Lines: 96
- Snippet: # A generic, single database configuration.

### backend/pyproject.toml
- Size: 2855 bytes
- Lines: 127
- Sections: build-system, project, project.optional-dependencies, project.scripts, tool.hatch.build.targets.wheel, tool.pytest.ini_options, tool.ruff, tool.ruff.isort, tool.mypy, tool.coverage.run, tool.coverage.report

### backend/scripts/ensure_e2e_role_users.py
- Size: 4343 bytes
- Lines: 140
- Classes: None
- Functions: _display_name

### backend/scripts/quantize_models.py
- Size: 1673 bytes
- Lines: 56
- Classes: None
- Functions: quantize_model

### backend/scripts/seed_test_users.py
- Size: 5797 bytes
- Lines: 145
- Classes: None
- Functions: None

### backend/src/sensei/__init__.py
- Size: 56 bytes
- Lines: 4
- Classes: None
- Functions: None

### backend/src/sensei/api/__init__.py
- Size: 1982 bytes
- Lines: 95
- Classes: None
- Functions: None

### backend/src/sensei/api/deps.py
- Size: 12453 bytes
- Lines: 442
- Classes: PermissionChecker, RoleChecker, RateLimiter, PaginationParams
- Functions: require_permission, require_role

### backend/src/sensei/api/exceptions.py
- Size: 14696 bytes
- Lines: 518
- Classes: SenseiException, NotFoundError, ConflictError, BadRequestError, UnauthorizedError, ForbiddenError, UnprocessableEntityError, RateLimitError, ServiceUnavailableError, BusinessRuleViolationError, StateTransitionError, ApprovalRequiredError, FileOperationError, ExternalServiceError
- Functions: register_exception_handlers

### backend/src/sensei/api/repository.py
- Size: 22583 bytes
- Lines: 720
- Classes: BaseRepository
- Functions: None

### backend/src/sensei/api/schemas.py
- Size: 12009 bytes
- Lines: 469
- Classes: APIResponse, PaginatedResponse, PaginationMeta, ErrorResponse, ValidationErrorDetail, ValidationErrorResponse, IDRequest, IDsRequest, BulkDeleteRequest, SortOrder, SearchRequest, FilterOperator, FilterRequest, AuditInfo, EntityMeta, StatusUpdateRequest, ArchiveRequest, AttachmentInfo, AttachmentUploadResponse, HealthStatus
- Functions: success_response, error_response, paginated_response

### backend/src/sensei/api/utils.py
- Size: 16099 bytes
- Lines: 677
- Classes: None
- Functions: parse_sort_param, parse_filter_param, _parse_filter_value, _parse_single_value, build_response, build_paginated_response, build_created_response, build_updated_response, build_deleted_response, model_to_dict, models_to_dicts, to_schema, to_schemas, apply_partial_update, validate_file_extension, validate_file_size, generate_unique_filename, get_content_type, validate_uuid, validate_uuids

### backend/src/sensei/api/v1/__init__.py
- Size: 6373 bytes
- Lines: 138
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/__init__.py
- Size: 128 bytes
- Lines: 6
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/a3.py
- Size: 37896 bytes
- Lines: 1263
- Classes: A3Create, A3Update, A3SectionResponse, A3Response, A3ReviewData, A3ApprovalData, SectionCreate, SectionUpdate, SectionComplete, SectionComment
- Functions: _now_utc, _parse_enum

### backend/src/sensei/api/v1/endpoints/accounts.py
- Size: 29113 bytes
- Lines: 942
- Classes: AddressSchema, AccountBase, AccountCreate, AccountUpdate, AccountResponse, AccountListResponse, AccountStatsResponse
- Functions: account_to_response, account_to_list_response

### backend/src/sensei/api/v1/endpoints/admin.py
- Size: 13825 bytes
- Lines: 371
- Classes: AdminStatsResponse, AdminGateBase, AdminGateResponse, AdminGateCreate, AdminGateUpdate, ReorderGatesRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/ai_health.py
- Size: 1258 bytes
- Lines: 43
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/analytics.py
- Size: 4417 bytes
- Lines: 113
- Classes: None
- Functions: get_analytics_warehouse_service

### backend/src/sensei/api/v1/endpoints/andon.py
- Size: 41885 bytes
- Lines: 1258
- Classes: AndonEventBase, AndonEventCreate, AndonEventUpdate, AndonAcknowledge, AndonResolve, AndonEscalate, AndonEventResponse, AndonEscalationCreate, AndonEscalationUpdate, AndonEscalationResponse, RecurrencePatternCreate, RecurrencePatternResponse, AndonAnalytics, AndonDashboardStats
- Functions: _now_utc, _parse_enum

### backend/src/sensei/api/v1/endpoints/andon_escalation.py
- Size: 21891 bytes
- Lines: 614
- Classes: AndonEventInput, StationInput, ProductInput, A3Input, CheckEscalationsRequest, DetectPatternsRequest, LinkEventsRequest, ThresholdsUpdateRequest, PatternSummaryRequest, GenerateA3Request, RecurrencePatternInput, RecurrencePatternResponse, A3TemplateResponse, EscalationResultResponse, ThresholdsResponse, LinkedEventResponse, LinkEventsResponse, PatternSummaryResponse, PatternTypesResponse, EscalationReasonsResponse
- Functions: get_service, _pattern_to_response, _template_to_response, _pattern_type_from_string, _input_to_pattern, check_for_escalations, detect_patterns, get_pattern_summary, generate_a3_template, link_events_to_a3, get_thresholds, update_thresholds, get_pattern_types, get_escalation_reasons

### backend/src/sensei/api/v1/endpoints/attachments.py
- Size: 29062 bytes
- Lines: 943
- Classes: AttachmentBase, AttachmentCreate, AttachmentUpdate, AttachmentResponse, VersionCreate, VersionResponse
- Functions: detect_category, get_file_extension, generate_storage_key

### backend/src/sensei/api/v1/endpoints/audit_logs.py
- Size: 17671 bytes
- Lines: 610
- Classes: AuditLogResponse, AuditSummary
- Functions: None

### backend/src/sensei/api/v1/endpoints/auth.py
- Size: 14328 bytes
- Lines: 514
- Classes: LoginRequest, TokenResponse, TwoFactorRequiredResponse, RefreshTokenRequest, PasswordResetRequest, PasswordResetConfirm, ChangePasswordRequest, VerifyEmailRequest, MessageResponse, RegisterRequest
- Functions: _split_full_name

### backend/src/sensei/api/v1/endpoints/backup_scheduler.py
- Size: 17657 bytes
- Lines: 510
- Classes: ScheduleCreateRequest, ScheduleUpdateRequest, ScheduleResponse, ExecutionResponse, RPOComplianceResponse, RTOComplianceResponse, ReadinessResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/backups.py
- Size: 14276 bytes
- Lines: 479
- Classes: BackupResponse, RestoreTestResponse, BackupSummaryResponse, RPOStatusResponse, RTOStatusResponse, CreateBackupRequest, RestoreBackupRequest, RetentionPolicyRequest
- Functions: get_backup_service

### backend/src/sensei/api/v1/endpoints/chaos_testing.py
- Size: 33842 bytes
- Lines: 1134
- Classes: CreateScenarioRequest, ScenarioResponse, FailureInjectionResponse, SystemStateResponse, CreateJobRetryTestRequest, JobRetryTestResponse, SimulateJobRequest, JobRetryValidationResponse, DegradationTestResponse, RegisterCircuitBreakerRequest, CircuitBreakerResponse, CreateCircuitBreakerTestRequest, CircuitBreakerTestResponse, CreateTestRunRequest, TestRunResponse, RecordRecoveryMetricsRequest, RecoveryMetricsResponse, ChaosSummaryResponse
- Functions: validate_failure_type, validate_component_type, validate_circuit_state, create_scenario, list_scenarios, get_scenario, delete_scenario, inject_failure, remove_failure, get_active_failures, get_system_state, create_job_retry_test, list_job_retry_tests, get_job_retry_test, simulate_job_execution, validate_job_retry, create_degradation_test, list_degradation_tests, execute_degradation_test, register_circuit_breaker

### backend/src/sensei/api/v1/endpoints/cognitive_obeya.py
- Size: 3321 bytes
- Lines: 101
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/common_thread.py
- Size: 3865 bytes
- Lines: 124
- Classes: CommonThreadNodeResponse, CommonThreadEdgeResponse, CommonThreadTraceResponse, CommonThreadBindRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/conditions.py
- Size: 32699 bytes
- Lines: 990
- Classes: PlaceholderSchema, ConditionTemplateResponse, CreateTemplateRequest, UpdateTemplateRequest, AppliedConditionResponse, ApplyConditionRequest, ApplyConditionSetRequest, AcknowledgeConditionRequest, ResolveHardStopRequest, UpdateConditionTextRequest, ReorderConditionsRequest, ConditionSetResponse, CreateConditionSetRequest, UpdateConditionSetRequest, CopyConditionsRequest, RenderTemplateRequest, ValidationResult, TemplateUsageStats, CategoryStats
- Functions: _template_to_response, _applied_to_response, _set_to_response, _get_service, _parse_category, _parse_condition_type, _parse_scope, _parse_placeholder_type, _schema_to_placeholder

### backend/src/sensei/api/v1/endpoints/contacts.py
- Size: 30395 bytes
- Lines: 992
- Classes: ContactBase, ContactCreate, ContactUpdate, ContactResponse, ContactListResponse, AccountContactRequest, AccountContactResponse, ContactAccountInfo
- Functions: contact_to_response, contact_to_list_response

### backend/src/sensei/api/v1/endpoints/context_bus.py
- Size: 2563 bytes
- Lines: 83
- Classes: ContextNodeResponse, ContextEdgeResponse, ContextPackResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/ctq.py
- Size: 29623 bytes
- Lines: 934
- Classes: CTQCreate, CTQUpdate, CTQResponse, MeasurementCreate, MeasurementUpdate, MeasurementResponse
- Functions: _now_utc, _parse_enum

### backend/src/sensei/api/v1/endpoints/data_lineage.py
- Size: 2339 bytes
- Lines: 78
- Classes: LineageNodeResponse, LineageEdgeResponse, LineageGraphResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/dev_bootstrap.py
- Size: 3830 bytes
- Lines: 116
- Classes: BootstrapUserRequest, BootstrapUserResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/dev_e2e.py
- Size: 3032 bytes
- Lines: 108
- Classes: SeedLineageResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/disaster_recovery_drill.py
- Size: 26910 bytes
- Lines: 812
- Classes: RPOTargetCreate, RTOTargetCreate, RPOTargetResponse, RTOTargetResponse, ConfigurationCreate, ConfigurationResponse, ScheduleCreate, ScheduleResponse, ScheduleToggle, BackupInfoModel, DrillStart, StepResponse, ExecutionResponse, StepExecute, DrillComplete, DrillFail, DrillResultResponse, DrillSummary, ComplianceReportResponse
- Functions: _serialize_rpo_target, _serialize_rto_target, _serialize_configuration, _serialize_schedule, _serialize_step, _serialize_execution, _serialize_result, _serialize_compliance_report, _parse_recovery_target, _parse_drill_type

### backend/src/sensei/api/v1/endpoints/edge_ai.py
- Size: 2425 bytes
- Lines: 71
- Classes: SensorReadingRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/escalation_policy.py
- Size: 17354 bytes
- Lines: 525
- Classes: EscalationLevelConfigSchema, EscalationPolicyResponse, EscalationThresholdsResponse, EscalationItemResponse, EscalationResultResponse, ApprovalInput, RiskInput, AndonInput, DetectApprovalsRequest, DetectRisksRequest, DetectAndonsRequest, FullScanRequest, FullScanResponse, UpdateThresholdRequest, UpdateRiskThresholdRequest
- Functions: _item_to_response, _result_to_response, _policy_to_response, list_policies, get_policy, get_thresholds, update_approval_threshold, update_risk_threshold, detect_aging_approvals, detect_value_based_approvals, detect_high_severity_risks, detect_overdue_risks, detect_andon_sla_breaches, get_target_types, get_escalation_reasons, get_escalation_levels, get_escalation_priorities, get_escalation_statuses, get_target_role

### backend/src/sensei/api/v1/endpoints/exceptions.py
- Size: 17457 bytes
- Lines: 599
- Classes: ExceptionResponse, ExceptionsListResponse, SummaryResponse, BadgeResponse, NavigationBadgesResponse, TrendPoint, TrendsResponse, CreateExceptionRequest, EscalateRequest, ResolveRequest, BlockRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/executive_intel.py
- Size: 7413 bytes
- Lines: 210
- Classes: NL2SQLRequest, NL2SQLResponse, EmployeeRiskRequest, EmployeeRiskResponse
- Functions: _roles_for_user, _coerce_exec_role, _normalize

### backend/src/sensei/api/v1/endpoints/factory_launchpad.py
- Size: 3233 bytes
- Lines: 90
- Classes: SiteRegisterRequest, LevelUpdateRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/gm_onboarding.py
- Size: 12865 bytes
- Lines: 464
- Classes: OnboardingStepResponse, OnboardingProgressResponse, TourSpotResponse, KeyMetricResponse, FirstActionResponse, ChecklistItemResponse, StartOnboardingRequest, CompleteStepRequest, OnboardingSummaryResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/health.py
- Size: 396 bytes
- Lines: 18
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/hr.py
- Size: 2407 bytes
- Lines: 71
- Classes: HRStats, DepartmentHeadcount, ExpiringCert
- Functions: None

### backend/src/sensei/api/v1/endpoints/kanban.py
- Size: 45847 bytes
- Lines: 1423
- Classes: ColumnConfig, SwimlaneConfig, KanbanBoardCreate, KanbanBoardUpdate, KanbanBoardResponse, KanbanCardCreate, KanbanCardUpdate, KanbanCardMoveRequest, KanbanTaskMoveRequest, KanbanCardBlockRequest, KanbanCardUnblockRequest, WIPOverrideRequest, KanbanCardResponse, KanbanCardHistoryResponse, KanbanMetricsResponse, BoardStatsResponse
- Functions: _now_utc, _parse_enum

### backend/src/sensei/api/v1/endpoints/kpi.py
- Size: 27965 bytes
- Lines: 938
- Classes: ThresholdSchema, DataSourceSchema, KPIDefinitionCreateRequest, KPIDefinitionUpdateRequest, KPIDefinitionResponse, KPIValueRecordRequest, KPIValueResponse, KPICalculationRequest, KPICalculationResponse, KPITrendResponse, DashboardCreateRequest, DashboardUpdateRequest, DashboardResponse, DashboardDataResponse, MudaNudgesRequest, MudaNudgeResponse
- Functions: _definition_to_response, generate_muda_nudges, _value_to_response, _dashboard_to_response

### backend/src/sensei/api/v1/endpoints/learning.py
- Size: 45366 bytes
- Lines: 1496
- Classes: SocraticRAGRequest, SocraticRAGSource, SocraticRAGPrompt, SocraticRAGResponse, ModuleCreate, ModuleUpdate, ModuleResponse, UnitCreate, UnitUpdate, UnitResponse, ProgressUpdate, ProgressResponse, AssessmentCreate, AssessmentUpdate, AssessmentResponse, PathCreate, PathUpdate, PathResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/lsw.py
- Size: 26435 bytes
- Lines: 845
- Classes: TemplateCreateRequest, TemplateUpdateRequest, TemplateResponse, InstanceResponse, ChecklistResponse, GenerationResultResponse, CompleteItemRequest, SkipItemRequest, DeferItemRequest, AddFindingRequest, ComplianceStatsResponse
- Functions: _template_to_response, _instance_to_response, _checklist_to_response

### backend/src/sensei/api/v1/endpoints/maintenance.py
- Size: 1969 bytes
- Lines: 54
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/notification_triggers.py
- Size: 20828 bytes
- Lines: 709
- Classes: TaskInput, RFQInput, QuoteInput, CertificationInput, UserInput, EvaluateTriggersRequest, GeneratedNotificationResponse, EvaluationResultResponse, TriggerConditionResponse, TriggerUpdateRequest, SnoozeRequest, AcknowledgeRequest, ClearSnoozeRequest, SnoozeSettingsResponse
- Functions: get_service, get_runner, _parse_uuid, _build_users_map, _notification_to_response, _trigger_to_response

### backend/src/sensei/api/v1/endpoints/obeya.py
- Size: 34967 bytes
- Lines: 1201
- Classes: ObeyaItemCreate, ObeyaItemUpdate, ObeyaItemResolve, SQDCPSafetyMetric, SQDCPQualityMetric, SQDCPDeliveryMetric, SQDCPCostMetric, SQDCPPeopleMetric, SQDCPMetricsResponse, ObeyaItemResponse, EscalationData, CommentCreate, CommentUpdate, CommentResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/opportunities.py
- Size: 34103 bytes
- Lines: 1165
- Classes: OpportunityBase, OpportunityCreate, OpportunityUpdate, OpportunityResponse, OpportunityListResponse, NoteBase, NoteCreate, NoteUpdate, NoteResponse, StageChangeRequest, CloseWonRequest, CloseLostRequest
- Functions: opportunity_to_response, opportunity_to_list_response, note_to_response

### backend/src/sensei/api/v1/endpoints/production_cells.py
- Size: 42476 bytes
- Lines: 1252
- Classes: ProductionCellCreate, ProductionCellUpdate, ProductionCellResponse, ProductionCellListResponse, CellPerformanceCreate, CellPerformanceUpdate, CellPerformanceResponse, CellPerformanceListResponse, CellStatsResponse, CellDailyOEEResponse
- Functions: cell_to_response, performance_to_response

### backend/src/sensei/api/v1/endpoints/products.py
- Size: 39177 bytes
- Lines: 1243
- Classes: ProductBase, ProductCreate, ProductUpdate, ProductResponse, ProductListResponse, BOMItemBase, BOMItemCreate, BOMItemUpdate, BOMItemResponse, RoutingBase, RoutingCreate, RoutingUpdate, RoutingResponse
- Functions: product_to_response, product_to_list_response, bom_item_to_response, routing_to_response

### backend/src/sensei/api/v1/endpoints/project_management.py
- Size: 99210 bytes
- Lines: 2864
- Classes: ProjectActivityResponse, ProjectCreate, ProjectUpdate, ProjectResponse, ProjectMemberCreate, ProjectMemberResponse, EpicCreate, EpicUpdate, EpicResponse, SprintCreate, SprintUpdate, SprintResponse, UserStoryCreate, UserStoryUpdate, UserStoryResponse, SubtaskCreate, SubtaskUpdate, SubtaskResponse, StoryCommentCreate, StoryCommentResponse
- Functions: _now_utc, _parse_enum, _user_id, _is_superuser

### backend/src/sensei/api/v1/endpoints/quality.py
- Size: 91422 bytes
- Lines: 2657
- Classes: NonConformanceBase, NonConformanceCreate, NonConformanceUpdate, NCRInvestigationData, NCRDispositionData, NCRCloseData, NCRStatsResponse, TimelineEventResponse, NonConformanceResponse, CAPABase, CAPACreate, CAPAUpdate, CAPAVerifyData, CAPARejectData, CAPACloseData, CAPAStatsResponse, CAPAActionResponse, CAPAResponse, CAPAActionCreate, CAPAActionUpdate
- Functions: _parse_enum, nc_to_response, _capa_action_to_response, capa_to_response, inspection_plan_to_response, inspection_record_to_response

### backend/src/sensei/api/v1/endpoints/quote_approval_time_tracking.py
- Size: 18642 bytes
- Lines: 626
- Classes: QuoteApprovalContextRequest, StartApprovalRequest, MakeDecisionRequest, QuickApproveRequest, UpdateCriterionRequest, AbandonRequest, SetTargetRequest, CriterionResponse, ContextResponse, SessionResponse, CountdownResponse, QuickOptionResponse, PerformanceResponse, QuoteSummaryResponse, LeaderboardEntryResponse, TargetResponse
- Functions: get_service, validate_uuid, validate_decision, validate_reason, validate_criterion_status, build_context, start_approval_session, get_session, get_countdown_status, make_decision, quick_approve, update_criterion, abandon_session, get_quote_sessions, get_approver_pending, get_quick_options, get_approver_performance, get_quote_summary, get_leaderboard, get_targets

### backend/src/sensei/api/v1/endpoints/quote_quality.py
- Size: 24312 bytes
- Lines: 625
- Classes: LineItemInput, AssumptionInput, SupplierQuoteInput, CTQLinkInput, QuoteQualityCheckRequest, CheckConfigInput, CheckWithConfigRequest, CheckItemResponse, QualityCheckResponse, BlockingIssuesResponse, QuickCheckResponse, CheckCategoriesResponse, CheckSeveritiesResponse, DefaultConfigResponse
- Functions: _convert_check_item, _convert_result, _request_to_quote_data, _request_to_config, _get_category_description, _get_severity_description

### backend/src/sensei/api/v1/endpoints/quotes.py
- Size: 45505 bytes
- Lines: 1564
- Classes: QuoteBase, QuoteCreate, QuoteUpdate, QuoteResponse, QuoteListResponse, LineItemBase, LineItemCreate, LineItemUpdate, LineItemResponse, VersionResponse, ApprovalRequest, SendQuoteRequest
- Functions: quote_to_response, quote_to_list_response, line_item_to_response, version_to_response

### backend/src/sensei/api/v1/endpoints/rbac_security_audit.py
- Size: 22216 bytes
- Lines: 743
- Classes: RegisterRoleRequest, RegisterPermissionRequest, RegisterUserRoleRequest, RegisterAuditLogRequest, RecordAccessRequest, ResolveFindingRequest, RoleResponse, PermissionResponse, UserRoleResponse, AuditLogResponse, AccessPatternResponse, FindingResponse, FindingsSummaryResponse, ComplianceReportResponse, VerificationResultResponse
- Functions: get_service, validate_uuid, validate_severity, validate_category, register_role, get_roles, get_role, register_permission, get_permissions, register_user_role, get_user_roles, get_user_role_assignments, register_audit_log, get_audit_logs, record_access_pattern, get_access_patterns, verify_role_configuration, verify_permission_configuration, verify_user_assignments, verify_audit_logs

### backend/src/sensei/api/v1/endpoints/rfq_time_tracking.py
- Size: 21727 bytes
- Lines: 751
- Classes: StartSessionRequest, PauseSessionRequest, CompleteSessionRequest, AbandonSessionRequest, SetTargetRequest, AcknowledgeAlertRequest, PauseResponse, SessionResponse, SessionStatusResponse, AlertResponse, TargetResponse, PerformanceStatsResponse, UserEfficiencyResponse, DailyBreakdownResponse, LeaderboardEntryResponse, RFQSummaryResponse, CleanupResponse
- Functions: get_service, validate_task_type, validate_uuid, start_session, get_session, check_session_status, pause_session, resume_session, complete_session, abandon_session, get_active_session, get_user_active_sessions, get_entity_sessions, get_session_alerts, get_pending_alerts, acknowledge_alert, get_all_targets, get_target, set_target, get_performance_stats

### backend/src/sensei/api/v1/endpoints/rfqs.py
- Size: 44460 bytes
- Lines: 1523
- Classes: RFQBase, RFQCreate, RFQUpdate, RFQResponse, RFQListResponse, QuestionBase, QuestionCreate, QuestionUpdate, QuestionResponse, CompletenessResponse, MissingInfoEmailResponse, QualifyRequest, QualifyResponse, TaskGenerationResponse
- Functions: rfq_to_response, rfq_to_list_response, question_to_response

### backend/src/sensei/api/v1/endpoints/risk.py
- Size: 37844 bytes
- Lines: 1224
- Classes: RiskCreate, RiskUpdate, RiskResponse, ResidualAssessmentData, OccurrenceData, MitigationCreate, MitigationUpdate, MitigationResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/saved_views.py
- Size: 20692 bytes
- Lines: 754
- Classes: FilterConditionRequest, SortFieldRequest, ColumnConfigRequest, CreateViewRequest, UpdateViewRequest, DuplicateViewRequest, SetDefaultRequest, ApplyViewRequest, FilterConditionResponse, SortFieldResponse, ColumnConfigResponse, SavedViewResponse, ViewFilterResultResponse, ViewListResponse
- Functions: get_service, _parse_uuid, _parse_entity_type, _parse_operator, _parse_filter_logic, _parse_date_preset, _parse_sort_direction, _parse_visibility, _condition_from_request, _sort_field_from_request, _column_from_request, _view_to_response

### backend/src/sensei/api/v1/endpoints/search.py
- Size: 17094 bytes
- Lines: 603
- Classes: SearchResultResponse, SearchResultSetResponse, QuickSearchResultResponse, SuggestionsResponse, IndexDocumentRequest, IndexAccountRequest, IndexRFQRequest, IndexQuoteRequest, IndexTaskRequest, IndexStatsResponse
- Functions: get_service, _parse_uuid, _parse_datetime, _parse_entity_type, _parse_sort_field, _parse_sort_order

### backend/src/sensei/api/v1/endpoints/stale_detection.py
- Size: 14702 bytes
- Lines: 380
- Classes: StaleThresholdResponse, StaleEntityResponse, StaleDetectionResultResponse, StaleDetectionRequest, FullScanSummaryResponse, FullScanRequest
- Functions: None

### backend/src/sensei/api/v1/endpoints/standard_work.py
- Size: 40036 bytes
- Lines: 1186
- Classes: StandardWorkBase, StandardWorkCreate, StandardWorkUpdate, StandardWorkSubmit, StandardWorkApprove, StandardWorkReject, StandardWorkRevise, ContentStep, ContentUpdate, StandardWorkResponse, StandardWorkVersionResponse
- Functions: _now_utc, _today, _parse_enum

### backend/src/sensei/api/v1/endpoints/state_machines.py
- Size: 7017 bytes
- Lines: 246
- Classes: TransitionCheckRequest, TransitionCheckResponse, TransitionRequirement, StateInfo, StateMachineInfo
- Functions: None

### backend/src/sensei/api/v1/endpoints/supply_chain.py
- Size: 2041 bytes
- Lines: 53
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/tasks.py
- Size: 35563 bytes
- Lines: 1280
- Classes: ChecklistItem, TaskCreate, TaskUpdate, TaskBulkUpdate, TaskMove, TaskBulkDelete, TaskResponse, TimeEntry, CommentCreate, CommentUpdate, CommentResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/today.py
- Size: 31022 bytes
- Lines: 1024
- Classes: PriorityCreateSchema, PriorityResponseSchema, SetTopPrioritiesSchema, RiskCreateSchema, RiskResponseSchema, CommitmentCreateSchema, CommitmentResponseSchema, AbnormalityCreateSchema, AbnormalityResponseSchema, MicroDrillCreateSchema, MicroDrillResponseSchema, DrillCompletionSchema, DrillCompletionResultSchema, DrillProgressSchema, LSWChecklistSummarySchema, QuickMetricSchema, RisksByCategorySchema, TodayScreenDataSchema
- Functions: _priority_to_response, _risk_to_response, _commitment_to_response, _abnormality_to_response, _drill_to_response

### backend/src/sensei/api/v1/endpoints/training.py
- Size: 57213 bytes
- Lines: 1692
- Classes: SkillBase, SkillCreate, SkillUpdate, SkillResponse, SkillRequirementBase, SkillRequirementCreate, SkillRequirementUpdate, SkillRequirementResponse, TrainingBase, TrainingCreate, TrainingUpdate, TrainingResponse, ParticipantEnroll, ParticipantUpdate, ParticipantComplete, ParticipantResponse, UserSkillCreate, UserSkillUpdate, UserSkillCertify, UserSkillResponse
- Functions: _now_utc, _today, _parse_enum

### backend/src/sensei/api/v1/endpoints/training_matrix.py
- Size: 24262 bytes
- Lines: 750
- Classes: SkillCellSchema, MatrixRowSchema, SkillColumnSchema, TrainingMatrixResponse, SkillGapSchema, GapAnalysisResponse, ExpiringCertificationSchema, RecertificationTaskSchema, ExpirationAlertResponse, UserSkillSummaryResponse, StationReadinessResponse, ThresholdsResponse, ThresholdUpdateRequest, GenerateMatrixRequest, GapAnalysisRequest, ExpirationCheckRequest, UserSkillSummaryRequest, StationReadinessRequest
- Functions: get_service, generate_matrix, generate_mock_matrix, analyze_gaps, get_gap_summary, check_expirations, get_expiration_thresholds, update_expiration_threshold, get_user_skill_summary, get_station_readiness, get_gap_severities, get_urgency_levels, _convert_matrix_result, _convert_gap_result, _convert_expiration_result

### backend/src/sensei/api/v1/endpoints/users.py
- Size: 20005 bytes
- Lines: 741
- Classes: UserBase, UserCreate, UserUpdate, AdminUserUpdate, UserResponse, UserWithRolesResponse, UserListResponse, TOTPSetupResponse, TOTPVerifyRequest, BackupCodesResponse, MessageResponse
- Functions: None

### backend/src/sensei/api/v1/endpoints/websockets.py
- Size: 1228 bytes
- Lines: 36
- Classes: None
- Functions: None

### backend/src/sensei/api/v1/endpoints/work_centers.py
- Size: 35855 bytes
- Lines: 1118
- Classes: WorkCenterBase, WorkCenterCreate, WorkCenterUpdate, WorkCenterResponse, WorkCenterListResponse, StationBase, StationCreate, StationUpdate, StationResponse, StationListResponse, WorkCenterStatsResponse
- Functions: work_center_to_response, work_center_to_list_response, station_to_response, station_to_list_response

### backend/src/sensei/api/v1/endpoints/work_orders.py
- Size: 54962 bytes
- Lines: 1595
- Classes: WorkOrderCreate, WorkOrderUpdate, WorkOrderHold, WorkOrderRelease, WorkOrderOperationResponse, WorkOrderResponse, JidokaSuggestionResponse, WorkOrderListResponse, WorkOrderStatsResponse, OperationCreate, OperationUpdate, OperationStart, OperationComplete
- Functions: operation_to_response, work_order_to_response, work_order_to_list_response

### backend/src/sensei/cli/__init__.py
- Size: 25 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/src/sensei/cli/knowledge.py
- Size: 16460 bytes
- Lines: 449
- Classes: None
- Functions: ingest, list, process, stats, verify_license, embed, search

### backend/src/sensei/cli/user.py
- Size: 2508 bytes
- Lines: 72
- Classes: None
- Functions: create_admin

### backend/src/sensei/core/__init__.py
- Size: 1175 bytes
- Lines: 56
- Classes: None
- Functions: None

### backend/src/sensei/core/auth.py
- Size: 22523 bytes
- Lines: 725
- Classes: AuthenticationError, InvalidCredentialsError, AccountLockedError, AccountInactiveError, EmailNotVerifiedError, TwoFactorRequiredError, InvalidTwoFactorError, TokenRevokedError, TokenExpiredError, PasswordResetError, AuthService
- Functions: get_auth_service

### backend/src/sensei/core/celery_app.py
- Size: 514 bytes
- Lines: 21
- Classes: None
- Functions: None

### backend/src/sensei/core/config.py
- Size: 4730 bytes
- Lines: 155
- Classes: Settings
- Functions: get_settings

### backend/src/sensei/core/database.py
- Size: 1693 bytes
- Lines: 70
- Classes: Base
- Functions: create_engine

### backend/src/sensei/core/enums.py
- Size: 4361 bytes
- Lines: 190
- Classes: Severity, WorkflowStatus, MetricStatus, ComparisonOperator, EntityType, JidokaAction, MetricCategory, DepartmentType, QuerySecurityLevel, EmployeeRiskType, PersonaType, ExportFormat
- Functions: None

### backend/src/sensei/core/pii.py
- Size: 1950 bytes
- Lines: 52
- Classes: None
- Functions: get_pii_service

### backend/src/sensei/core/redis.py
- Size: 1292 bytes
- Lines: 53
- Classes: None
- Functions: create_redis_client

### backend/src/sensei/core/security.py
- Size: 16498 bytes
- Lines: 627
- Classes: TokenData, TokenPayload, TokenPair, TOTPSetupResult
- Functions: hash_password, _prepare_password_for_bcrypt, verify_password, needs_rehash, create_access_token, create_refresh_token, create_token_pair, decode_token, verify_token, get_token_jti, generate_totp_secret, get_totp_provisioning_uri, generate_totp_qr_code, setup_totp, verify_totp, generate_backup_codes, _normalize_backup_code, hash_backup_codes, verify_backup_code, generate_secure_token

### backend/src/sensei/core/storage.py
- Size: 6016 bytes
- Lines: 208
- Classes: None
- Functions: create_storage_client, generate_file_key, compute_file_hash, generate_presigned_url

### backend/src/sensei/core/time.py
- Size: 849 bytes
- Lines: 32
- Classes: None
- Functions: now_utc, utcnow_naive

### backend/src/sensei/core/websocket.py
- Size: 1920 bytes
- Lines: 49
- Classes: ConnectionManager
- Functions: get_websocket_manager

### backend/src/sensei/main.py
- Size: 8788 bytes
- Lines: 238
- Classes: None
- Functions: create_application

### backend/src/sensei/middleware/__init__.py
- Size: 325 bytes
- Lines: 12
- Classes: None
- Functions: None

### backend/src/sensei/middleware/correlation.py
- Size: 1068 bytes
- Lines: 37
- Classes: CorrelationIdMiddleware
- Functions: None

### backend/src/sensei/middleware/logging.py
- Size: 2257 bytes
- Lines: 72
- Classes: StructuredLoggingMiddleware
- Functions: None

### backend/src/sensei/middleware/secure_headers.py
- Size: 25106 bytes
- Lines: 758
- Classes: CSPDirective, XFrameOption, ReferrerPolicy, CSPConfig, HSTSConfig, PermissionsPolicyConfig, CacheControlConfig, HeaderOverride, CSPViolationReport, SecureHeadersMiddleware, SecureHeadersASGIMiddleware
- Functions: None

### backend/src/sensei/middleware/timing.py
- Size: 772 bytes
- Lines: 28
- Classes: TimingMiddleware
- Functions: None

### backend/src/sensei/ml/cbm_predictor.py
- Size: 21173 bytes
- Lines: 584
- Classes: ConditionBasedMaintenancePredictor
- Functions: _utcnow

### backend/src/sensei/ml/evaluation.py
- Size: 12643 bytes
- Lines: 373
- Classes: EvaluationResults, ModelEvaluator
- Functions: None

### backend/src/sensei/ml/evidence_detector.py
- Size: 14203 bytes
- Lines: 389
- Classes: MissingEvidenceDetector
- Functions: analyze_all_reports

### backend/src/sensei/ml/lesson_recommender.py
- Size: 14158 bytes
- Lines: 407
- Classes: LessonRecommender
- Functions: _utcnow, generate_recommendations_for_all_users

### backend/src/sensei/ml/mlops.py
- Size: 16723 bytes
- Lines: 493
- Classes: ModelStatus, ModelMetadata, ModelRegistry, ModelMonitor, MLPipeline, ABTestManager
- Functions: _utcnow

### backend/src/sensei/ml/safety_gates.py
- Size: 20443 bytes
- Lines: 507
- Classes: SafetyCheckStatus, SafetyCheckResult, SafetyGateResults, SafetyGateConfig, MLSafetyGates
- Functions: None

### backend/src/sensei/models/__init__.py
- Size: 9056 bytes
- Lines: 410
- Classes: None
- Functions: None

### backend/src/sensei/models/a3.py
- Size: 12843 bytes
- Lines: 416
- Classes: A3Type, A3Status, A3Priority, A3SectionType, A3, A3Section
- Functions: None

### backend/src/sensei/models/account.py
- Size: 14679 bytes
- Lines: 447
- Classes: AccountType, AccountStatus, AccountTier, Account, ContactRole, Contact, AccountContact
- Functions: None

### backend/src/sensei/models/admin.py
- Size: 4244 bytes
- Lines: 80
- Classes: AdminGate, ApprovalWorkflow, Template, LearningCadence, FeatureFlag
- Functions: None

### backend/src/sensei/models/analytics.py
- Size: 2501 bytes
- Lines: 73
- Classes: DailySnapshot, DimensionSchema, FactSchema, ExportedRecord
- Functions: None

### backend/src/sensei/models/andon.py
- Size: 13635 bytes
- Lines: 412
- Classes: AndonType, EscalationLevel, ResponseStatus, AndonEvent, AndonEscalation, AndonRecurrencePattern
- Functions: None

### backend/src/sensei/models/attachment.py
- Size: 9090 bytes
- Lines: 289
- Classes: AttachmentCategory, AttachmentStatus, Attachment, AttachmentVersion
- Functions: None

### backend/src/sensei/models/audit_log.py
- Size: 5736 bytes
- Lines: 174
- Classes: AuditAction, AuditLog
- Functions: None

### backend/src/sensei/models/base.py
- Size: 5473 bytes
- Lines: 199
- Classes: Base, TimestampMixin, AuditMixin, SoftDeleteMixin, StatusMixin
- Functions: generate_ulid

### backend/src/sensei/models/business_continuity.py
- Size: 3058 bytes
- Lines: 77
- Classes: QueuedEvent, CriticalityRule, RTORPOConfig, RestoreRehearsal
- Functions: None

### backend/src/sensei/models/cognitive_obeya.py
- Size: 5571 bytes
- Lines: 96
- Classes: MetricRecord, CausalLinkRecord, TrendWarningRecord, SiloAlertRecord, ResourceRebalanceRecord, HeijunkaSuggestionRecord
- Functions: None

### backend/src/sensei/models/ctq.py
- Size: 11094 bytes
- Lines: 320
- Classes: CTQCategory, CTQPriority, CTQStatus, MeasurementResult, CTQ, CTQMeasurement
- Functions: None

### backend/src/sensei/models/data_lineage.py
- Size: 2103 bytes
- Lines: 62
- Classes: DataLineageLink
- Functions: None

### backend/src/sensei/models/exception.py
- Size: 2044 bytes
- Lines: 40
- Classes: ExceptionRecord
- Functions: None

### backend/src/sensei/models/finance.py
- Size: 2074 bytes
- Lines: 53
- Classes: GLAccount, OpeningBalance
- Functions: None

### backend/src/sensei/models/inventory.py
- Size: 1234 bytes
- Lines: 38
- Classes: InventoryLevel
- Functions: None

### backend/src/sensei/models/kanban.py
- Size: 16676 bytes
- Lines: 514
- Classes: BoardType, CardType, CardStatus, CardPriority, KanbanBoard, KanbanCard, KanbanCardHistory, KanbanMetrics
- Functions: None

### backend/src/sensei/models/knowledge_pack.py
- Size: 8743 bytes
- Lines: 288
- Classes: LicenseType, ContentFormat, TaxonomyTag, KnowledgeDocument, KnowledgeChunk, IngestionLog
- Functions: None

### backend/src/sensei/models/learning.py
- Size: 18097 bytes
- Lines: 603
- Classes: LearningCategory, ContentType, DifficultyLevel, LearningStatus, LearningModule, LearningUnit, ProgressStatus, UserLearningProgress, LearningAssessment, LearningPath, LearningProgress
- Functions: None

### backend/src/sensei/models/maintenance.py
- Size: 2358 bytes
- Lines: 55
- Classes: ConditionReading, MaintenanceRecord
- Functions: None

### backend/src/sensei/models/migration.py
- Size: 1218 bytes
- Lines: 38
- Classes: ImportBatch
- Functions: None

### backend/src/sensei/models/obeya.py
- Size: 10862 bytes
- Lines: 372
- Classes: ObeyaCategory, ObeyaStatus, ObeyaPriority, ObeyaBoard, ObeyaItemStatus, ObeyaItemType, ObeyaItem, ObeyaComment
- Functions: None

### backend/src/sensei/models/opportunity.py
- Size: 11472 bytes
- Lines: 375
- Classes: OpportunityStage, OpportunityType, OpportunitySource, Opportunity, NoteType, OpportunityNote
- Functions: None

### backend/src/sensei/models/ot_network.py
- Size: 6124 bytes
- Lines: 176
- Classes: ZoneType, CertificateStatus, ZoneViolationSeverity, NetworkZone, ZoneViolation, EdgeCertificate
- Functions: None

### backend/src/sensei/models/pii.py
- Size: 5718 bytes
- Lines: 97
- Classes: PIIField, DataSubject, Consent, PIIAccessLog, DeletionRequest
- Functions: None

### backend/src/sensei/models/product.py
- Size: 11750 bytes
- Lines: 371
- Classes: ProductStatus, UnitOfMeasure, Product, BOMItem, Routing
- Functions: None

### backend/src/sensei/models/production.py
- Size: 11428 bytes
- Lines: 352
- Classes: CellType, CellStatus, ShiftNumber, ProductionCell, CellPerformance
- Functions: None

### backend/src/sensei/models/project_management.py
- Size: 42179 bytes
- Lines: 1294
- Classes: ProjectStatus, ProjectType, SprintStatus, UserStoryStatus, EpicStatus, IssueType, IssueSeverity, IssueStatus, IssuePriority, MilestoneType, WikiPageType, BoardType, Project, ProjectMember, Epic, UserStory, Subtask, StoryComment, StoryHistory, Sprint
- Functions: None

### backend/src/sensei/models/qualification.py
- Size: 12939 bytes
- Lines: 420
- Classes: QualificationResult, CriterionCategory, QualificationStatus, QualificationDecision, CriterionType, ScoreValue, Qualification, QualificationCriterion, QualificationScore
- Functions: None

### backend/src/sensei/models/quality.py
- Size: 30831 bytes
- Lines: 961
- Classes: NCType, NCSource, NCSeverity, NCStatus, NCDisposition, RootCauseCategory, CAPAType, CAPASourceType, CAPAStatus, CAPAPriority, VerificationStatus, EffectivenessStatus, CAPAActionType, CAPAActionStatus, InspectionType, InspectionResult, NonConformance, CAPAStateHistory, CAPA, CAPAAction
- Functions: None

### backend/src/sensei/models/quote.py
- Size: 21909 bytes
- Lines: 693
- Classes: QuoteStatus, ApprovalStatus, LineItemType, VersionStatus, SupplierQuoteStatus, Quote, QuoteVersion, QuoteLineItem, SupplierQuoteStatus, SupplierQuote, SupplierQuoteItem
- Functions: None

### backend/src/sensei/models/reasoning_trace.py
- Size: 1306 bytes
- Lines: 41
- Classes: ReasoningTrace
- Functions: None

### backend/src/sensei/models/rfq.py
- Size: 15400 bytes
- Lines: 494
- Classes: RFQStatus, RFQPriority, RFQSource, RFQ, QuestionStatus, RFQQuestion, RFQAttachmentType, RFQAttachment
- Functions: None

### backend/src/sensei/models/risk.py
- Size: 13862 bytes
- Lines: 444
- Classes: RiskCategory, RiskStatus, RiskSeverity, RiskLikelihood, Risk, MitigationStatus, RiskMitigation
- Functions: None

### backend/src/sensei/models/segment.py
- Size: 6385 bytes
- Lines: 218
- Classes: SegmentModule, SegmentVisibility, Segment, SegmentShare, SegmentUsage
- Functions: None

### backend/src/sensei/models/standard_work.py
- Size: 10344 bytes
- Lines: 306
- Classes: StandardWorkStatus, StandardWorkType, StandardWork, StandardWorkVersion
- Functions: None

### backend/src/sensei/models/strategic.py
- Size: 3518 bytes
- Lines: 65
- Classes: NL2SQLQueryRecord, EmployeeRiskAssessmentRecord, ScenarioResultRecord, VarianceAlertRecord
- Functions: None

### backend/src/sensei/models/strategic_v2.py
- Size: 8949 bytes
- Lines: 193
- Classes: InspectionFeedback, TrainingSample, AgentAnalysisRecord, ConsensusDebateRecord, KnowledgeSourceRecord, SemanticChunkRecord, SiteMaturityRecord, LevelUpChecklistRecord, UIActionAuditRecord, LessonDeliveryRecord, StandardWorkEvolutionRecord
- Functions: None

### backend/src/sensei/models/task.py
- Size: 13331 bytes
- Lines: 469
- Classes: TaskStatus, TaskPriority, TaskType, Task, TaskComment, NotificationType, NotificationPriority, NotificationStatus, NotificationChannel, Notification
- Functions: None

### backend/src/sensei/models/tps.py
- Size: 4843 bytes
- Lines: 90
- Classes: PDCACycleRecord, KataSessionRecord, MudaDetectionRecord, TPSAndonEventRecord, JidokaResponseRecord, UserTPSStats
- Functions: None

### backend/src/sensei/models/training.py
- Size: 17838 bytes
- Lines: 575
- Classes: SkillCategory, TrainingType, TrainingStatus, EnrollmentStatus, AttendanceStatus, CertificationStatus, Skill, SkillRequirement, Training, TrainingParticipant, UserSkill
- Functions: None

### backend/src/sensei/models/user.py
- Size: 14676 bytes
- Lines: 483
- Classes: UserStatus, RoleType, User, Role, Permission, UserRole, RolePermission, RefreshToken
- Functions: None

### backend/src/sensei/models/work_center.py
- Size: 9282 bytes
- Lines: 277
- Classes: WorkCenterStatus, StationType, StationStatus, WorkCenter, Station
- Functions: None

### backend/src/sensei/models/work_order.py
- Size: 13654 bytes
- Lines: 405
- Classes: WorkOrderStatus, WorkOrderPriority, OperationStatus, HoldReason, WorkOrder, WorkOrderOperation
- Functions: None

### backend/src/sensei/scripts/train_system.py
- Size: 2794 bytes
- Lines: 75
- Classes: None
- Functions: None

### backend/src/sensei/services/__init__.py
- Size: 14370 bytes
- Lines: 615
- Classes: None
- Functions: None

### backend/src/sensei/services/ai/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/ai/advanced_rag.py
- Size: 48999 bytes
- Lines: 1507
- Classes: ContentType, ChunkingStrategy, RetrievalStrategy, RerankingModel, EmbeddingModel, IndexType, FeedbackType, DocumentMetadata, Chunk, TableChunk, ImageChunk, RetrievalResult, RetrievalContext, QueryAnalysis, RetrievalFeedback, RAGConfig, ChunkerBase, SemanticChunker, HierarchicalChunker, QueryAnalyzer
- Functions: None

### backend/src/sensei/services/ai/ai_content_drafting.py
- Size: 39417 bytes
- Lines: 1157
- Classes: ContentType, DraftStatus, ConfidenceLevel, KnowledgeSourceType, A3SectionType, KnowledgeSource, DraftContent, A3DraftRequest, A3Context, A3SectionDraft, A3FullDraft, DraftHistory, KnowledgeBase, AIDraftingService
- Functions: get_ai_drafting_service, reset_ai_drafting_service

### backend/src/sensei/services/ai/ai_ctq_summarization.py
- Size: 55527 bytes
- Lines: 1477
- Classes: SummaryType, AnalysisPeriod, RiskLevel, TrendDirection, CapabilityStatus, RecommendationType, OutputFormat, MeasurementData, CTQSpec, StatisticalSummary, TrendAnalysis, RiskAssessment, Recommendation, CTQSummary, MultiCTQSummary, AICTQSummarizationService
- Functions: None

### backend/src/sensei/services/ai/ai_email_drafting.py
- Size: 46536 bytes
- Lines: 1365
- Classes: EmailTone, EmailPurpose, DraftStatus, Language, ComplianceCheckType, SuggestionType, Recipient, EmailContext, GenerationRequest, GeneratedDraft, ComplianceCheck, ImprovementSuggestion, EmailTemplate, DraftHistory, AIProviderConfig, AIEmailDraftingService
- Functions: _utcnow

### backend/src/sensei/services/ai/ai_learning_recommendations.py
- Size: 44838 bytes
- Lines: 1271
- Classes: RecommendationType, RecommendationPriority, LearningGoal, SkillLevel, LearningStyle, ContextTrigger, ContentCategory, DifficultyLevel, UserProfile, LearningUnitInfo, ProgressData, SkillAssessment, LearningRecommendation, SkillGap, LearningPath, SpacedRepetitionSchedule, RecommendationSet, AILearningRecommendationsService
- Functions: None

### backend/src/sensei/services/ai/ai_qualification_advisory.py
- Size: 51952 bytes
- Lines: 1430
- Classes: AdvisoryType, DecisionRecommendation, ConfidenceLevel, RiskCategory, RiskSeverity, GapSeverity, ActionPriority, ScoringRationale, CriterionData, ScoreData, QualificationData, ScoringRecommendation, IdentifiedRisk, Gap, RecommendedAction, DecisionSupport, BenchmarkResult, QualificationAdvisory, AIQualificationAdvisoryService
- Functions: None

### backend/src/sensei/services/ai/ai_readiness.py
- Size: 5543 bytes
- Lines: 162
- Classes: AIComponentStatus, AIReadinessReport, AIReadinessService
- Functions: get_ai_readiness_service

### backend/src/sensei/services/ai/ai_reasoning.py
- Size: 20732 bytes
- Lines: 651
- Classes: RerankerModel, AnomalyType, SearchChunk, SearchResult, Correction, FewShotExample, PredictionExplanation, AnomalyEvent, AIReasoningService
- Functions: _utcnow

### backend/src/sensei/services/ai/continuous_learning.py
- Size: 39984 bytes
- Lines: 1183
- Classes: LearningMode, RetrainingTrigger, FeedbackSource, LearningFeedback, RetrainingJob, RetrainingConfig, ModelLearningState, FeedbackCollector, IncrementalLearner, RetrainingManager, ContinuousLearningService
- Functions: _utcnow, create_retraining_celery_tasks, get_continuous_learning_service, reset_continuous_learning_service

### backend/src/sensei/services/ai/document_intelligence.py
- Size: 56582 bytes
- Lines: 1671
- Classes: DocumentType, ElementType, ProcessingStrategy, ExtractionConfidence, EnrichmentType, BoundingBox, DocumentElement, TableCell, ExtractedTable, ExtractedFigure, KeyValuePair, GDTCallout, DimensionCallout, TitleBlockData, DocumentPage, ProcessedDocument, ProcessingConfig, LayoutModel, TableStructureModel, OCREngine
- Functions: None

### backend/src/sensei/services/ai/domain_knowledge_seeder.py
- Size: 16588 bytes
- Lines: 343
- Classes: DomainKnowledgeSeeder
- Functions: get_knowledge_seeder

### backend/src/sensei/services/ai/enhanced_ml_pipeline.py
- Size: 67069 bytes
- Lines: 1953
- Classes: ModelType, ModelStage, ModelStatus, DriftType, DriftSeverity, FeatureType, ExperimentStatus, PipelineStage, FeatureDefinition, FeatureVector, FeatureGroup, TrainingDataset, ModelMetrics, ModelVersion, ModelRegistry, DriftDetectionResult, Experiment, ABTest, PredictionLog, MonitoringAlert
- Functions: _utcnow, get_ml_pipeline_service

### backend/src/sensei/services/ai/hybrid_search.py
- Size: 41233 bytes
- Lines: 1281
- Classes: SearchMode, RerankingStrategy, ChunkingStrategy, ChunkMetadata, Chunk, SearchResult, SearchQuery, SearchResponse, RerankCacheEntry, TokenEstimator, RecursiveCharacterSplitter, TokenAwareChunker, RerankCache, CrossEncoderReranker, ONNXCrossEncoder, _InlineTFIDFScorer, SemanticSearcher, KeywordSearcher, InMemorySemanticSearcher, InMemoryKeywordSearcher
- Functions: _utcnow, create_hybrid_search_engine, create_chunker

### backend/src/sensei/services/ai/knowledge_embeddings.py
- Size: 13025 bytes
- Lines: 395
- Classes: EmbeddingService, KnowledgeEmbeddingService, SemanticSearchService
- Functions: None

### backend/src/sensei/services/ai/knowledge_enrichment.py
- Size: 40459 bytes
- Lines: 1168
- Classes: SourceType, ContentFormat, IngestionStatus, ChunkType, TaxonomyCategory, KnowledgeSource, AcquisitionJob, SemanticChunk, EmbeddingRecord, AlignmentResult, KnowledgePack, AuditEntry, CrossDomainSynthesizer, KnowledgeEnrichmentService
- Functions: None

### backend/src/sensei/services/ai/knowledge_ingestion.py
- Size: 23533 bytes
- Lines: 720
- Classes: LicenseVerifier, ContentFetcher, ContentNormalizer, SemanticChunker, QualityFilter, TaxonomyTagger, KnowledgePackIngestionService
- Functions: None

### backend/src/sensei/services/ai/meta_sensei.py
- Size: 59067 bytes
- Lines: 1567
- Classes: TemplateType, DeduplicationStrategy, SiteTermType, DocSyncAction, CodeIssueType, CodeIssueSeverity, RefactoringType, UserCorrection, StandardTemplate, KnowledgeChunk, DeduplicationResult, SiteTerm, SiteReranker, FeatureDetection, DocSyncResult, PlanItem, PlanSyncResult, CodeIssue, RefactoringSuggestion, QuotePerformance
- Functions: create_knowledge_synthesizer, create_deduplicator, create_site_learner, create_doc_sync, create_plan_tracker, create_code_auditor, create_refactoring_suggestor, create_practice_extractor, create_a3_evolver, create_meta_sensei

### backend/src/sensei/services/ai/nlp_command_palette.py
- Size: 34756 bytes
- Lines: 1066
- Classes: ActionType, EntityType, ParseConfidence, Entity, ParsedAction, ConversationTurn, ConversationSession, SymbolMatch, FuzzyMatcher, ActionParser, ConversationManager, NLPCommandPalette
- Functions: _utcnow, create_nlp_command_palette

### backend/src/sensei/services/ai/onnx_cross_encoder.py
- Size: 20415 bytes
- Lines: 571
- Classes: CrossEncoderConfig, RerankCacheEntry, CrossEncoderCache, TFIDFScorer, ONNXCrossEncoder
- Functions: _utcnow, get_cross_encoder

### backend/src/sensei/services/ai/onnx_model_init.py
- Size: 14836 bytes
- Lines: 458
- Classes: ModelTier, ModelValidationResult, ModelRegistryStatus, ONNXModelValidator, ONNXModelRegistry
- Functions: get_model_registry

### backend/src/sensei/services/ai/onnx_text_embeddings.py
- Size: 6814 bytes
- Lines: 201
- Classes: EmbeddingConfig, ONNXTextEmbedder
- Functions: _l2_normalize, _mean_pool, get_onnx_embedder

### backend/src/sensei/services/ai/reasoning_engine.py
- Size: 37307 bytes
- Lines: 1020
- Classes: A3Phase, LeanWasteCategory, MudaType, MentorPersona, PromptType, KPITrend, KPIMetric, Countermeasure, A3Report, CountermeasureCorrelation, ChallengingPrompt, RootCauseSuggestion, WebSocketMessage, A3PatternAnalyzer, SocraticMentor, FiveWhysAssistant, SenseiReasoningEngine
- Functions: _utcnow, create_reasoning_engine

### backend/src/sensei/services/ai/self_improving_rag.py
- Size: 38050 bytes
- Lines: 1117
- Classes: ChunkUtilityStatus, DocumentQuality, ReindexPriority, IndexingMode, ChunkMetadata, ChunkUtilityEvent, DocumentMetrics, ReindexJob, ThrottleConfig, ChunkUtilityTracker, VectorIndexStore, InMemoryVectorStore, IncrementalIndexManager, ThrottleManager, ReindexScheduler, DocumentProcessor, SimpleDocumentProcessor, SelfImprovingRAGService
- Functions: _utcnow, create_self_improving_rag

### backend/src/sensei/services/ai/semantic_anomaly_detection.py
- Size: 36944 bytes
- Lines: 1049
- Classes: AlertSensitivity, AnomalyType, EventType, SentimentLevel, UrgencyLevel, ProcessEvent, SentimentResult, SequencePattern, TimingAnomaly, Anomaly, AlertConfig, Alert, SentimentAnalyzer, SequenceAnalyzer, AlertManager, AnomalyDetectionEngine
- Functions: create_anomaly_detector

### backend/src/sensei/services/ai/socratic_pedagogy_rag.py
- Size: 6490 bytes
- Lines: 213
- Classes: RetrievedUnit, SocraticPedagogyRAG
- Functions: _tokenize, _count_term_hits, score_learning_unit, rank_learning_units, _rank_learning_units_by_embeddings, build_pedagogical_context

### backend/src/sensei/services/ai/virtual_assistant.py
- Size: 45678 bytes
- Lines: 1308
- Classes: SLAStatus, ItemType, NotificationType, NotificationPriority, EntityCategory, BriefingSection, SLADeadline, TimeToFailure, Notification, NotificationRule, CalendarEvent, ExtractedEntity, BriefingItem, BriefingNote, CriticalPathCalculator, SLAWatchdog, CalendarEntityExtractor, BriefingNoteGenerator, MeetingPreparationAI, SenseiVirtualAssistant
- Functions: create_virtual_assistant

### backend/src/sensei/services/ai/visual_quality_inspection.py
- Size: 56123 bytes
- Lines: 1573
- Classes: DefectCategory, DefectSeverity, InspectionDecision, ModelType, AnomalyMethod, ZoneType, BoundingBox, SegmentationMask, InspectionZone, DetectedDefect, AnomalyMap, InspectionResult, InspectionBatch, SyntheticDefectGenerator, VisionEnrichmentSuite, InspectionConfig, AnomalyDetector, DefectDetector, PatchCoreDetector, YOLODefectDetector
- Functions: _utcnow

### backend/src/sensei/services/ai/world_class_document_ai.py
- Size: 52212 bytes
- Lines: 1563
- Classes: DocumentCategory, ElementType, ProcessingStrategy, VisionLLMProvider, GDTSymbol, ToleranceType, BoundingBox, DocumentElement, TableCell, ExtractedTable, GDTCallout, DimensionCallout, TitleBlockData, KeyValuePair, ExtractedFigure, DocumentPage, ProcessedDocument, LayoutAnalyzer, TableStructureRecognizer, VisionLLMEnricher
- Functions: None

### backend/src/sensei/services/ai/xai_service.py
- Size: 34778 bytes
- Lines: 1041
- Classes: ExplanationType, DecisionCategory, EvidenceSource, ConfidenceLevel, AuditEventType, EvidenceChunk, FeatureContribution, CounterfactualScenario, DecisionExplanation, AIDecision, AuditEvent, ReasoningStep, ModelInfo, EvidenceRetriever, FeatureAnalyzer, CounterfactualGenerator, ExplanationGenerator, AIReasoningAuditTrail, XAIService
- Functions: create_xai_service, create_explanation_generator, create_audit_trail, create_evidence_retriever

### backend/src/sensei/services/automated_feedback_loops.py
- Size: 31954 bytes
- Lines: 919
- Classes: CorrectionType, CorrectionStatus, ConflictResolutionStrategy, ContextType, ModelVersion, UserInfo, CorrectionMetadata, Correction, CorrectionGroup, RetrievedCorrection, LearningStore, InMemoryLearningStore, ConflictResolver, FewShotExample, FewShotInjector, CorrectionVersionManager, FeedbackLoopManager
- Functions: create_feedback_loop_manager

### backend/src/sensei/services/autosave_drafts.py
- Size: 26639 bytes
- Lines: 847
- Classes: DraftType, DraftStatus, ConflictResolution, DraftVersion, Draft, DraftRecovery, ConflictInfo, AutosaveDraftsService
- Functions: None

### backend/src/sensei/services/bulk_actions.py
- Size: 32397 bytes
- Lines: 975
- Classes: BulkActionType, EntityType, BulkActionStatus, ItemResultStatus, BulkActionItemResult, BulkActionResult, BulkActionRequest, ValidationResult, BulkActionsService
- Functions: None

### backend/src/sensei/services/certification_tracking.py
- Size: 19679 bytes
- Lines: 579
- Classes: CertificationStandard, CertificationStatus, CertificationRecord, CertificationEvidence, RecertificationNudge, CertificationTrackingService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/conditions_library.py
- Size: 59723 bytes
- Lines: 1529
- Classes: ConditionCategory, ConditionType, ConditionScope, PlaceholderType, Placeholder, ConditionTemplate, AppliedCondition, ConditionSet, ConditionsLibraryService
- Functions: _utcnow, get_conditions_library_service, get_default_template_codes, get_default_condition_set_ids

### backend/src/sensei/services/content_scanning.py
- Size: 33504 bytes
- Lines: 1108
- Classes: ScanResult, ThreatCategory, ContentType, ScanMode, ThreatSignature, AllowedFileType, ContentPolicy, ScanFinding, ScanReport, QuarantineEntry, ContentScanningService
- Functions: None

### backend/src/sensei/services/core/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/core/access_review.py
- Size: 26165 bytes
- Lines: 826
- Classes: ReviewFrequency, ReviewStatus, AttestationStatus, AccessType, RiskLevel, AccessItem, UserAccess, Attestation, ReviewCampaign, ReviewReminder, AccessViolation, AccessReviewService
- Functions: None

### backend/src/sensei/services/core/activity_feed.py
- Size: 32777 bytes
- Lines: 1051
- Classes: ActivityType, EntityType, ActivityPriority, ActivityActor, ActivityTarget, ActivityMetadata, Activity, AggregatedActivity, FeedSubscription, ActivityFeedService
- Functions: None

### backend/src/sensei/services/core/alerting_config.py
- Size: 34620 bytes
- Lines: 1089
- Classes: AlertSeverity, AlertStatus, NotificationChannel, ComparisonOperator, AggregationFunction, ThresholdCondition, NotificationTarget, NotificationRoute, AlertRule, Alert, Silence, AlertGroup, AlertHistory, AlertingConfigService
- Functions: None

### backend/src/sensei/services/core/backup_scheduler.py
- Size: 18634 bytes
- Lines: 533
- Classes: ScheduleType, ScheduleStatus, BackupSchedule, ScheduleExecution, BackupSchedulerService
- Functions: None

### backend/src/sensei/services/core/business_continuity.py
- Size: 14661 bytes
- Lines: 448
- Classes: EventPriority, ConflictResolutionStrategy, QueuedEventStatus, RehearsalStatus, QueuedEvent, CriticalityRule, RTORPOConfig, RestoreRehearsal, BusinessContinuityService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/core/common_thread.py
- Size: 9025 bytes
- Lines: 277
- Classes: CommonThreadNode, CommonThreadEdge, CommonThreadTrace, CommonThreadService
- Functions: get_common_thread_service

### backend/src/sensei/services/core/context_bus.py
- Size: 10056 bytes
- Lines: 263
- Classes: ContextEntitySnapshot, ContextPack, ContextService
- Functions: get_context_service

### backend/src/sensei/services/core/data_hygiene_nudges.py
- Size: 35158 bytes
- Lines: 1000
- Classes: NudgeType, NudgePriority, NudgeStatus, EntityType, FieldRule, Nudge, NudgeSuppressionRule, HygieneReport, EntityHygieneScore, DataHygieneNudgesService
- Functions: None

### backend/src/sensei/services/core/data_lineage.py
- Size: 15944 bytes
- Lines: 481
- Classes: LineageNode, LineageEdge, LineageGraph, DataLineageService
- Functions: get_data_lineage_service

### backend/src/sensei/services/core/data_quality.py
- Size: 24063 bytes
- Lines: 658
- Classes: ValidationType, Severity, ValidationRule, ValidationError, ValidationResult, DataQualityService
- Functions: None

### backend/src/sensei/services/core/data_retention.py
- Size: 32084 bytes
- Lines: 960
- Classes: EntityType, RetentionAction, RetentionStatus, PolicyStatus, RetentionPolicy, LegalHold, RetentionRecord, RetentionJob, RetentionReport, DataRetentionService
- Functions: None

### backend/src/sensei/services/core/database_backup.py
- Size: 21464 bytes
- Lines: 604
- Classes: BackupStrategy, BackupStatus, RestoreStatus, BackupMetadata, RestoreTest, BackupSchedule, DatabaseBackupService
- Functions: None

### backend/src/sensei/services/core/disaster_recovery_drill.py
- Size: 36008 bytes
- Lines: 1031
- Classes: DrillType, DrillStatus, RecoveryTarget, ComplianceLevel, RPOTarget, RTOTarget, BackupInfo, DrillStep, DrillConfiguration, DrillExecution, DrillSchedule, DrillResult, ComplianceReport, DisasterRecoveryDrillService
- Functions: get_dr_drill_service, reset_dr_drill_service

### backend/src/sensei/services/core/edge_ai.py
- Size: 36002 bytes
- Lines: 1080
- Classes: AnomalyType, SeverityLevel, SyncPriority, MessageType, ConnectionState, SensorReading, AnomalyDetection, MachineHealthStatus, EdgeMessage, SyncResult, CNNModelConfig, Conv1DLayer, MaxPool1DLayer, DenseLayer, EdgeCNN1D, PredictiveMaintenanceEngine, ProtobufLikeEncoder, PriorityMessageQueue, EdgeToCoreSyncManager, EdgeOrchestrator
- Functions: get_edge_orchestrator, create_predictive_maintenance_engine, create_edge_sync_manager, create_cnn_model, create_priority_queue

### backend/src/sensei/services/core/email_service.py
- Size: 15280 bytes
- Lines: 441
- Classes: EmailType, EmailMessage, EmailService
- Functions: get_email_service, reset_email_service

### backend/src/sensei/services/core/factory_launchpad.py
- Size: 44600 bytes
- Lines: 1263
- Classes: MaturityLevel, MaturityTransitionStatus, FeatureModule, ChecklistItemStatus, ValidationSeverity, SiteStatus, HardwareAssetType, HardwareAssetStatus, SiteConfig, ChecklistItem, LevelUpChecklist, ValidationIssue, ActionValidationResult, HardwareAsset, RolloutProgress, FeatureAccess, UIVisibilityConfig, MaturityManager, UIVisibilityManager, HardwareRolloutTracker
- Functions: get_factory_launchpad, create_factory_launchpad, create_maturity_manager, create_ui_visibility_manager, create_hardware_tracker

### backend/src/sensei/services/core/health_checks.py
- Size: 16649 bytes
- Lines: 485
- Classes: HealthStatus, DependencyType, HealthCheck, DependencyHealth, ResourceMetrics, ScalingRecommendation, HealthCheckService
- Functions: _utcnow

### backend/src/sensei/services/core/identity_access.py
- Size: 8692 bytes
- Lines: 290
- Classes: SSOProtocol, DevicePosture, AccessDecision, SSOProvider, ConditionalAccessPolicy, AccessEvaluationResult, IdentityAccessService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/core/infrastructure_resilience.py
- Size: 17301 bytes
- Lines: 560
- Classes: HealthStatus, ServiceType, PerformanceMetrics, SlowQueryEvent, HealthCheckResult, DeepHealthReport, FileIntegrityResult, BackupRestoreResult, InfrastructureResilienceService
- Functions: _utcnow

### backend/src/sensei/services/core/local_first_infrastructure.py
- Size: 39809 bytes
- Lines: 1152
- Classes: ModelPrecision, ModelSize, CircuitState, ExecutionProvider, ModelConfig, InferenceResult, SystemResources, MemoryManager, CircuitBreaker, FallbackStrategy, RegexFallback, HeuristicFallback, FallbackManager, ONNXModelSession, ONNXModelManager, ONNXOptimizer, LocalFirstService
- Functions: get_local_first_service

### backend/src/sensei/services/core/notification_triggers.py
- Size: 42068 bytes
- Lines: 1009
- Classes: TriggerType, RecipientRole, NotificationChannel, NotificationPriority, SnoozeStatus, TriggerCondition, NotificationTarget, GeneratedNotification, TriggerEvaluationResult, UserSnoozeSettings, NotificationTriggersService, NotificationTriggersJobRunner
- Functions: None

### backend/src/sensei/services/core/onnx_edge_inference.py
- Size: 13170 bytes
- Lines: 372
- Classes: ONNXEdgeConfig, ONNXEdgeInference
- Functions: get_onnx_edge_inference

### backend/src/sensei/services/core/persona_management.py
- Size: 12811 bytes
- Lines: 417
- Classes: Persona, AuditEventType, User, AuditLogEntry, PersonaManagementService
- Functions: _utcnow

### backend/src/sensei/services/core/pii_controls.py
- Size: 34018 bytes
- Lines: 1026
- Classes: PIICategory, SensitivityLevel, MaskingType, ConsentType, ConsentStatus, PIIAccessType, PIIReport, PIIControlsService
- Functions: None

### backend/src/sensei/services/core/privacy_compliance.py
- Size: 8425 bytes
- Lines: 266
- Classes: AttendanceEventType, DataCategory, AttendanceEvent, RetentionPolicy, DeletionRun, PrivacyComplianceService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/core/query_optimization.py
- Size: 16819 bytes
- Lines: 446
- Classes: QueryType, PerformanceThreshold, QueryMetrics, IndexRecommendation, QueryAnalysis, QueryOptimizationService
- Functions: _utcnow

### backend/src/sensei/services/core/rbac_enhanced.py
- Size: 33851 bytes
- Lines: 1051
- Classes: Role, Module, Permission, FieldSecurityCategory, SoDRuleType, PermissionGrant, FeatureVisibility, FieldSecurityRule, SoDRule, SoDViolation, ImmutableAuditEntry, EnhancedRBACService
- Functions: _utcnow, _norm_roles

### backend/src/sensei/services/core/rbac_security_audit.py
- Size: 39237 bytes
- Lines: 1023
- Classes: AuditSeverity, AuditCategory, ComplianceStatus, AuditFinding, RoleConfig, PermissionConfig, UserRoleAssignment, AuditLogEntry, AccessPattern, ComplianceReport, RBACSecurityAuditService
- Functions: get_rbac_security_audit_service, reset_rbac_security_audit_service

### backend/src/sensei/services/core/search.py
- Size: 27314 bytes
- Lines: 858
- Classes: SearchableEntityType, SearchSortField, SearchSortOrder, SearchResult, SearchResultSet, SearchFilter, SearchableDocument, FullTextSearchService
- Functions: index_account, index_rfq, index_quote, index_task, index_a3, index_ctq

### backend/src/sensei/services/core/security_logging.py
- Size: 8367 bytes
- Lines: 265
- Classes: EventSeverity, EventCategory, AlertStatus, SecurityEvent, ThreatAlert, SecurityLoggingService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/core/setup_wizard.py
- Size: 37365 bytes
- Lines: 998
- Classes: WizardStatus, WizardStep, PipelineStageType, ApprovalThresholdType, LSWFrequency, RoleType, OrganizationProfile, PipelineStage, ApprovalThreshold, RoleAssignment, TemplateConfig, LSWChecklistItem, LSWCadenceConfig, ObeyaConfig, WizardStepData, WizardProgress, StartWizardRequest, StartWizardResponse, UpdateStepRequest, UpdateStepResponse
- Functions: get_default_pipeline_stages, get_default_approval_thresholds, get_default_lsw_items, get_default_obeya_config

### backend/src/sensei/services/core/state_machine.py
- Size: 24511 bytes
- Lines: 793
- Classes: TransitionError, TransitionRule, TransitionResult, StateMachine, StateMachineRegistry, GateEnforcer
- Functions: create_opportunity_state_machine, create_rfq_state_machine, create_qualification_state_machine, create_task_state_machine

### backend/src/sensei/services/core/template_cloning.py
- Size: 29959 bytes
- Lines: 933
- Classes: CloneableEntityType, TemplateCategory, CloneMode, FieldMapping, CloneOptions, Template, CloneResult, CloneHistory, TemplateCloningService
- Functions: None

### backend/src/sensei/services/device_management.py
- Size: 9212 bytes
- Lines: 311
- Classes: DeviceStatus, DeviceCommand, CommandStatus, DeviceProfile, EnrolledDevice, DeviceCommandRecord, DeviceManagementService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/document_regional.py
- Size: 35508 bytes
- Lines: 1117
- Classes: Region, Currency, DocumentType, TaxType, SignatureStatus, RegionalConfig, TaxRate, ContributionRate, LogoAsset, LetterheadTemplate, GeneratedDocument, InvoiceData, PayslipData, SOSReminder, AuditEntry, DocumentRegionalService
- Functions: None

### backend/src/sensei/services/ehs_safety.py
- Size: 47999 bytes
- Lines: 1365
- Classes: IncidentSeverity, IncidentType, IncidentStatus, BodyPart, HazardCategory, RiskLevel, PPEType, CertificationType, CertificationStatus, AlertPriority, SafetyIncident, JSAHazard, JobSafetyAnalysis, EmployeeCertification, SafetyAlert, JSAAcknowledgment, AuditPack, EHSSafetyService
- Functions: create_ehs_safety_service

### backend/src/sensei/services/erp_integration.py
- Size: 50248 bytes
- Lines: 1475
- Classes: ERPSystem, EntityType, SyncDirection, SyncStatus, ReconciliationStatus, CircuitState, MappingType, UoMType, FieldMapping, EntityMapping, UoMConversion, TaxCode, SyncRecord, ReconciliationItem, CircuitBreaker, WebhookConfig, SyncJob, SyncStatistics, FieldTransformer, ERPIntegrationService
- Functions: create_erp_integration_service

### backend/src/sensei/services/escalation_policy.py
- Size: 48575 bytes
- Lines: 1240
- Classes: EscalationTargetType, EscalationReason, EscalationLevel, EscalationStatus, EscalationPriority, EscalationPolicy, EscalationLevelConfig, EscalationItem, EscalationResult, EscalationPolicyService, EscalationJobRunner
- Functions: _utcnow

### backend/src/sensei/services/exceptions_aggregator.py
- Size: 24340 bytes
- Lines: 654
- Classes: ExceptionItem, ExceptionSummary, ExceptionTrend, NavigationBadge, ExceptionsAggregator
- Functions: get_exceptions_aggregator, create_exception

### backend/src/sensei/services/finance/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/finance/accounting_ledger.py
- Size: 33967 bytes
- Lines: 1000
- Classes: AccountType, EntryStatus, PeriodStatus, AuditEvent, ChartAccount, JournalLine, JournalEntry, AccountingPeriod, FXRate, PostedLine, TrialBalanceRow, Statement, AccountingLedgerService
- Functions: _now, _norm_roles, _q2, _require_any, _validate_currency, _validate_account_code

### backend/src/sensei/services/finance/accounts_payable.py
- Size: 39191 bytes
- Lines: 1242
- Classes: PRStatus, POStatus, InvoiceStatus, PaymentRunStatus, AuditEvent, PRLine, PurchaseRequisition, POLine, PurchaseOrder, ReceiptLine, GoodsReceipt, SupplierInvoiceLine, SupplierInvoice, MatchException, ThreeWayMatchResult, Payment, PaymentRun, APConfig, AccountsPayableService
- Functions: _now, _q2, _norm_roles, _norm_currency, _require_any

### backend/src/sensei/services/finance/accounts_receivable.py
- Size: 34094 bytes
- Lines: 1037
- Classes: SalesOrderStatus, InvoiceStatus, PaymentStatus, DisputeStatus, AuditEvent, CustomerCreditProfile, SalesOrderLine, SalesOrder, InvoiceLine, Invoice, PaymentAllocation, PaymentReceipt, InvoiceDispute, DunningAction, ARConfig, AccountsReceivableService
- Functions: _now, _q2, _norm_roles, _require_any, _norm_currency, _parse_quote_like

### backend/src/sensei/services/finance/cost_accounting.py
- Size: 33732 bytes
- Lines: 1018
- Classes: CostMethod, AuditEvent, StandardCost, MaterialIssue, DirectLaborBooking, OverheadBooking, CompletionReceipt, Shipment, WorkOrderCostState, VarianceBreakdown, WIPValuationRow, MarginRow, CostAccountingConfig, CostAccountingService
- Functions: _now, _q2, _norm_roles, _norm_currency, _require_any

### backend/src/sensei/services/finance/financial_operational_feedback.py
- Size: 7615 bytes
- Lines: 225
- Classes: ReconciliationIssueType, ReconciliationIssue, ReconciliationReport, QuoteCOGSVariance, FinancialOperationalFeedbackService
- Functions: None

### backend/src/sensei/services/finance/fixed_assets.py
- Size: 31657 bytes
- Lines: 1024
- Classes: DepreciationMethod, FixedAssetStatus, AssetEventType, AuditEvent, FixedAsset, DepreciationPosting, DisposalResult, AssetEvent, FixedAssetsConfig, FixedAssetsService
- Functions: _now, _q2, _norm_roles, _norm_currency, _require_any

### backend/src/sensei/services/finance/integration_reconciliation.py
- Size: 40761 bytes
- Lines: 1255
- Classes: SyncStatus, SyncDirection, ConflictResolution, BankTransactionType, ReconciliationStatus, ExceptionType, SyncContract, SyncOperation, ConflictRecord, BankTransaction, BankImportBatch, ReconciliationItem, ReconciliationException, ReconciliationSession, AuditEvent, IntegrationReconciliationService
- Functions: _utcnow, _norm_roles, _require_any

### backend/src/sensei/services/finance/payroll_labor_costing.py
- Size: 19217 bytes
- Lines: 568
- Classes: AttendanceEventType, TimecardStatus, VarianceType, VarianceStatus, AttendanceEvent, Timecard, VarianceRequest, LaborBooking, PayrollLaborCostingService
- Functions: _norm_roles

### backend/src/sensei/services/guardrails_performance.py
- Size: 32217 bytes
- Lines: 990
- Classes: ResourceType, TaskPriority, TaskStatus, PIIType, RedactionMethod, DriftSeverity, ResourceMetrics, AITask, LoadedModel, PIIMatch, RedactionResult, RedactionAuditEntry, PIIToken, SuggestionFeedback, DriftMetrics, PromptVariant, ConsistencyScore, ResourceMonitor, ModelManager, PIIRedactor
- Functions: create_resource_monitor, create_model_manager, create_pii_redactor, create_hitl_monitor

### backend/src/sensei/services/hr/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/hr/compensation_management.py
- Size: 23298 bytes
- Lines: 691
- Classes: CompensationType, ChangeStatus, ChangeReason, AuditEvent, PayBand, CompensationRecord, CompensationChange, CompensationManagementService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/hr/employee_lifecycle.py
- Size: 21936 bytes
- Lines: 623
- Classes: EmploymentStatus, ChecklistType, ChecklistStatus, ChecklistCategory, PersonnelDocumentType, EmployeeProfile, ChecklistItem, EmployeeChecklist, PersonnelDocument, EmployeeLifecycleService
- Functions: _require_tzaware, _norm_roles

### backend/src/sensei/services/hr/hr_case_management.py
- Size: 24951 bytes
- Lines: 814
- Classes: CaseType, CaseStatus, CasePriority, ActionType, AuditEvent, CaseEvidence, CaseNote, CaseAction, HRCase, HRCaseManagementService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/hr/leave_management.py
- Size: 32639 bytes
- Lines: 1030
- Classes: LeaveType, AccrualFrequency, LeaveRequestStatus, AuditEvent, AccrualPolicy, HolidayCalendar, PublicHoliday, LeaveBalance, LeaveRequest, PayrollLeaveExport, PayrollLeaveRecord, LeaveManagementService
- Functions: _norm_roles, _require_any, _utcnow

### backend/src/sensei/services/hr/recruiting.py
- Size: 31901 bytes
- Lines: 1010
- Classes: RequisitionStatus, CandidateStatus, InterviewType, InterviewResult, OfferStatus, AuditEvent, JobRequisition, Candidate, Interview, OfferLetter, RecruitingService
- Functions: _norm_roles, _require_any, _utcnow, _mask_pii

### backend/src/sensei/services/hr/staffing_roster.py
- Size: 14586 bytes
- Lines: 436
- Classes: ShiftType, AbsenceType, AbsenceStatus, RiskSeverity, ShiftDefinition, RosterSlot, Absence, SkillCoverageRisk, StaffingRosterService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/hr/talent_performance.py
- Size: 17718 bytes
- Lines: 577
- Classes: ReviewCycleType, ReviewStatus, A3ContributionType, SuggestionStatus, PraiseType, A3Contribution, Suggestion, OeeSnapshot, PerformanceReviewMetrics, PerformanceReview, SuccessionCandidate, PraiseMilestone, TalentPerformanceService
- Functions: _require_tzaware, _norm_roles

### backend/src/sensei/services/hr/training_matrix.py
- Size: 37170 bytes
- Lines: 958
- Classes: GapSeverity, ExpirationUrgency, CertificationStatusValue, SkillCellData, MatrixRow, SkillGap, ExpiringCertification, RecertificationTask, TrainingMatrixResult, GapAnalysisResult, ExpirationAlertResult, TrainingMatrixService
- Functions: _utcnow

### backend/src/sensei/services/hypercare.py
- Size: 14035 bytes
- Lines: 485
- Classes: FeedbackType, FeedbackStatus, ConfigChangeType, ChangeApprovalStatus, SeedStatus, ChecklistItemStatus, UserFeedback, ConfigChangeRequest, EnvironmentConfig, SeedJob, ChecklistItem, GoLiveChecklist, HypercareService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/incident_flow.py
- Size: 28241 bytes
- Lines: 855
- Classes: IncidentSeverity, IncidentStatus, IncidentCategory, NotificationChannel, EscalationTrigger, SeverityConfig, OnCallPerson, OnCallSchedule, EscalationLevel, EscalationPolicy, Incident, IncidentNotification, IncidentMetrics, IncidentFlowService
- Functions: None

### backend/src/sensei/services/inline_comments.py
- Size: 34335 bytes
- Text: no (binary or unsupported)

### backend/src/sensei/services/intelligent_ingestion.py
- Size: 35730 bytes
- Lines: 1085
- Classes: DocumentFormat, ParsingStrategy, ExtractionType, ConfidenceLevel, HITLReason, DocumentPage, TableCell, TableData, BOMEntry, ExtractedBOM, DrawingSpec, ParsingResult, StandardWorkVersion, StandardWorkDiff, OCREngine, VisionLLMParser, TableExtractor, MultiPageStitcher, StandardWorkManager, UniversalZeroShotParser
- Functions: create_document_parser

### backend/src/sensei/services/maintenance/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/maintenance/maintenance_tpm.py
- Size: 42199 bytes
- Lines: 1238
- Classes: AssetType, AssetStatus, Criticality, PMFrequencyType, PMStatus, WorkOrderType, WorkOrderStatus, DowntimeCategory, Asset, PMSchedule, MaintenanceWorkOrder, DowntimeEvent, OEEMetrics, SparePart, FailureRecord, MaintenanceService
- Functions: get_maintenance_service, create_maintenance_service

### backend/src/sensei/services/mentions_assignments.py
- Size: 41059 bytes
- Lines: 1131
- Classes: MentionType, AssignmentStatus, NotificationType, EntityType, Priority, Mention, Assignment, TaskFromComment, MentionNotification, UserSummary, TeamSummary, DueDateInfo, ParseMentionsRequest, ParseMentionsResponse, CreateAssignmentRequest, CreateAssignmentResponse, CreateTaskFromCommentRequest, CreateTaskFromCommentResponse, UpdateDueDateRequest, UpdateDueDateResponse
- Functions: extract_mentions_from_text, clean_mention_text, generate_task_title_from_comment, calculate_due_date_info, generate_due_date_from_text, format_mention_notification_message, generate_entity_link

### backend/src/sensei/services/missing_info_workflow.py
- Size: 41570 bytes
- Lines: 1183
- Classes: MissingFieldCategory, MissingFieldPriority, InfoRequestStatus, TaskStatus, ReminderFrequency, MissingFieldSpec, IdentifiedMissingField, InfoRequest, GeneratedTask, EmailTemplate, RFQData, AnalysisResult, WorkflowConfig, MissingInfoWorkflowService
- Functions: _utcnow, get_missing_info_workflow_service, reset_missing_info_workflow_service

### backend/src/sensei/services/ops/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/ops/a3_reasoning_gates.py
- Size: 9123 bytes
- Lines: 251
- Classes: GateSeverity, GateIssue
- Functions: _now_iso, _normalize, _contains_any, _extract_whys, evaluate_a3_section_update, build_gate_payload

### backend/src/sensei/services/ops/analytics_warehouse.py
- Size: 8171 bytes
- Lines: 268
- Classes: SnapshotStatus, DimensionType, FactType, AnalyticsWarehouseService
- Functions: _norm_roles, _utcnow

### backend/src/sensei/services/ops/andon_a3_escalation.py
- Size: 25182 bytes
- Lines: 695
- Classes: RecurrencePatternType, A3EscalationReason, A3EscalationStatus, RecurrencePattern, RecurrenceThresholds, A3Template, EscalationResult, AndonA3EscalationService, AndonA3EscalationJobRunner
- Functions: None

### backend/src/sensei/services/ops/ceo_control_plane.py
- Size: 29981 bytes
- Lines: 888
- Classes: RiskLevel, MetricType, NL2SQLQuery, EmployeeRiskAssessment, SkillMatrixEntry, SQDCPMetric, WarRoomDisplay, ScenarioResult, ProductionScenarioModeler, OrganizationalHealthHeatmap, VarianceAlert, CEOControlPlaneService
- Functions: _utcnow, _severity_from_deviation

### backend/src/sensei/services/ops/cognitive_obeya.py
- Size: 43980 bytes
- Lines: 1212
- Classes: TrendDirection, AlertType, MetricValue, CausalLink, TrendWarning, SiloAlert, ResourceRebalance, HeijunkaSuggestion, WorkCenterLoad, SkillProfile, PrescriptiveMetricAnalyzer, CrossFunctionalSynergyEngine, HeijunkaAdvisor, CognitiveObeya
- Functions: get_cognitive_obeya, create_cognitive_obeya, create_metric_analyzer, create_synergy_engine, create_heijunka_advisor

### backend/src/sensei/services/ops/gm_onboarding.py
- Size: 27278 bytes
- Lines: 776
- Classes: OnboardingStatus, OnboardingStepType, OnboardingStep, OnboardingChecklistItem, OnboardingProgress, GMDashboardTourSpot, GMKeyMetric, GMFirstAction, GMOnboardingService
- Functions: get_gm_onboarding_service

### backend/src/sensei/services/ops/jit_lean_learning.py
- Size: 45700 bytes
- Lines: 1236
- Classes: LessonCategory, TriggerType, LessonStatus, StandardWorkStatus, PerformerLevel, MicroLesson, LessonDelivery, KnowledgeDocument, KnowledgeLink, StandardWork, StandardWorkDraft, OperatorPerformance, BestPracticeSuggestion, MicroLessonEngine, KnowledgeRetrievalEngine, StandardWorkEvolutionEngine, JITLeanLearning
- Functions: create_jit_lean_learning, create_micro_lesson_engine, create_knowledge_retrieval_engine, create_standard_work_engine

### backend/src/sensei/services/ops/kpi_app_services.py
- Size: 1182 bytes
- Lines: 32
- Classes: None
- Functions: None

### backend/src/sensei/services/ops/kpi_metric_sources.py
- Size: 48582 bytes
- Lines: 1279
- Classes: MetricType, DataSourceType, AggregationPeriod, MetricCategory, FieldSource, EventSource, ComputationFormula, MetricDefinition, MetricValue, MetricTrend, KPIMetricSourcesService
- Functions: None

### backend/src/sensei/services/ops/kpi_metrics.py
- Size: 55138 bytes
- Lines: 1590
- Classes: SafeExpressionEvaluator, KPICategory, KPIUnit, KPIDirection, AggregationType, TrendDirection, KPIThreshold, KPIDataSource, KPIDefinition, KPIValue, KPITrend, KPIDashboard, KPICalculationResult, KPIService
- Functions: build_kpi_definition, get_default_kpi_ids, get_default_dashboard_ids

### backend/src/sensei/services/ops/metric_sources.py
- Size: 32279 bytes
- Lines: 763
- Classes: EventType, CalculationMethod, TimestampField, FieldMapping, FilterCondition, MetricSourceDefinition, MetricSourceValidation, MetricSourceUsage, MetricSourcesService
- Functions: None

### backend/src/sensei/services/ops/muda_contextual_nudging.py
- Size: 9762 bytes
- Lines: 254
- Classes: MudaNudge, MudaAwareContextualNudgingService
- Functions: None

### backend/src/sensei/services/ops/muda_nudging_scheduler.py
- Size: 3410 bytes
- Lines: 116
- Classes: MudaNudgingScheduleConfig, MudaNudgingSchedulerService
- Functions: None

### backend/src/sensei/services/ops/muda_nudging_worker.py
- Size: 4214 bytes
- Lines: 117
- Classes: MudaNudgingRunResult, MudaNudgingJobRunner
- Functions: None

### backend/src/sensei/services/ops/sensei_autopilot.py
- Size: 38852 bytes
- Lines: 1237
- Classes: HealthStatus, ServiceType, HealingActionType, BackupType, BackupStatus, ModelUpdateStatus, SlowQuery, IndexRecommendation, TableStats, StorageItem, CleanupResult, ServiceHealth, HealingAction, DataIntegrityCheck, Backup, RestoreResult, ModelVersion, DatabaseTuner, StorageManager, SelfHealingEngine
- Functions: create_autopilot, create_db_tuner, create_storage_manager, create_healing_engine, create_backup_manager

### backend/src/sensei/services/ops/sensei_command.py
- Size: 53644 bytes
- Lines: 1499
- Classes: KPIType, RiskLevel, RiskCategory, LearningMetricType, ExecutiveKPI, FinancialHealth, RiskItem, RiskHeatmap, SystemHealthStatus, LearningProgression, MaintenanceAuditEntry, NL2SQLQuery, StrategicBriefing, CrossSiloCorrelation, MarginLeakage, CohortAnalysis, Bottleneck, AuditTrailEntry, EmployeeAnalytics, TalentRiskAlert
- Functions: create_kpi_aggregator, create_financial_monitor, create_risk_generator, create_brain_dashboard, create_nl2sql_engine, create_briefing_generator, create_deep_analytics, create_audit_trail, create_ceo_view, create_employee_analytics, create_sensei_command

### backend/src/sensei/services/ops/sensei_nudges.py
- Size: 34001 bytes
- Lines: 960
- Classes: NudgeCategory, NudgeSeverity, NudgeTrigger, FormContext, NudgeRule, Nudge, NudgeFeedback, NudgeStats, SenseiNudgesService
- Functions: None

### backend/src/sensei/services/ops/today_screen.py
- Size: 70469 bytes
- Lines: 2046
- Classes: RiskCategory, AbnormalityType, CommitmentType, PriorityLevel, LSWChecklistStatus, ShopFloorAreaType, ShopFloorAlertSeverity, Priority, Risk, Commitment, Abnormality, MicroDrill, LSWChecklistSummary, QuickMetric, WorkOrderAtRisk, CriticalAndon, StationEfficiency, CellOEE, KanbanAlert, ExpiringCertification
- Functions: _utcnow, get_today_screen_service, reset_today_screen_service

### backend/src/sensei/services/ops/tps_knowledge_sources.py
- Size: 69309 bytes
- Lines: 1635
- Classes: SourceCategory, LicenseType, TopicArea, KnowledgeSource
- Functions: get_all_sources, get_sources_by_category, get_sources_by_topic, get_sources_by_license, get_high_quality_sources, get_sources_by_tags, get_source_statistics, generate_cli_commands

### backend/src/sensei/services/ops/tps_teacher.py
- Size: 47654 bytes
- Lines: 1352
- Classes: PDCAPhase, PhaseGateStatus, MudaType, KataStep, AndonStatus, PDCACycle, PhaseGateRequirement, CoachingPrompt, KataSession, MudaDetection, AndonEvent, JidokaResponse, PDCACoachingEngine, ImprovementKataAssistant, MudaDetectionEngine, JidokaMentor, MultiModalPDCACoach, KataGamificationService, TPSTeacher
- Functions: create_tps_teacher, create_pdca_engine, create_kata_assistant, create_muda_detector, create_jidoka_mentor

### backend/src/sensei/services/org_structure.py
- Size: 24764 bytes
- Lines: 779
- Classes: OrgUnitType, PositionType, PositionStatus, AssignmentStatus, AuditEvent, OrgUnit, Position, PositionAssignment, ReportingRelation, OrgStructureService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/ot_network_safety.py
- Size: 12259 bytes
- Lines: 385
- Classes: ZoneType, ZoneViolationSeverity, CertificateStatus, NetworkZone, ZoneViolation, EdgeCertificate, OTNetworkSafetyService
- Functions: None

### backend/src/sensei/services/ot_network_safety_db.py
- Size: 22511 bytes
- Lines: 700
- Classes: OTNetworkSafetyService
- Functions: _norm_roles, _utcnow, get_ot_network_safety_service

### backend/src/sensei/services/plm_drawing_control.py
- Size: 40113 bytes
- Lines: 1127
- Classes: RevisionStatus, DocumentType, ChangeType, ImpactType, AccessLevel, PLMSystem, DocumentRevision, ControlledDocument, RevisionLink, RevisionImpact, TrainingRecertification, ShopFloorAccess, DocumentAccess, PLMSyncRecord, ObsoleteWatermark, RevisionNumberGenerator, PLMDrawingControlService
- Functions: create_plm_drawing_control_service

### backend/src/sensei/services/production/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/production/dispatch_traveler.py
- Size: 28420 bytes
- Lines: 862
- Classes: OperationStatus, CheckpointType, CheckpointResult, DispatchPriority, AuditEvent, RouteOperation, Checkpoint, CheckpointRecord, Traveler, TravelerOperation, DispatchItem, MaterialsProvider, ToolsProvider, SkillsProvider, DispatchTravelerService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/production/jidoka_error_proofing.py
- Size: 10044 bytes
- Lines: 274
- Classes: JidokaSuggestion, JidokaErrorProofingService
- Functions: None

### backend/src/sensei/services/production/label_printing.py
- Size: 39505 bytes
- Lines: 1087
- Classes: LabelSize, BarcodeType, LabelType, PrinterType, PrintStatus, ScanErrorType, LabelTemplate, Printer, PrintJob, BarcodeValidation, GS1Element, ScanRecoveryWorkflow, LabelPrintingService
- Functions: create_label_printing_service

### backend/src/sensei/services/production/lot_serial_traceability.py
- Size: 39778 bytes
- Lines: 1126
- Classes: LotStatus, SerialStatus, TraceabilityDirection, GenealogyLinkType, CertificateType, RecallStatus, LotRecord, SerialRecord, GenealogyLink, Certificate, RecallRecord, WhereUsedResult, TraceabilityTree, LotSerialTraceabilityService
- Functions: create_lot_serial_service

### backend/src/sensei/services/production/lsw_scheduling.py
- Size: 34979 bytes
- Lines: 991
- Classes: LSWFrequency, LSWCategory, LSWItemStatus, DayOfWeek, LSWChecklistTemplate, LSWChecklistInstance, LSWChecklist, LSWReminder, LSWGenerationResult, LSWSchedulingService
- Functions: build_lsw_template, get_default_template_ids

### backend/src/sensei/services/production/mrp_lite.py
- Size: 25513 bytes
- Lines: 780
- Classes: RequirementType, SuggestionStatus, DemandType, AuditEvent, BOMComponent, InventoryLevel, DemandEntry, MRPSuggestion, MRPRunResult, MRPService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/production/production_scheduling.py
- Size: 16789 bytes
- Lines: 505
- Classes: TaskPriority, ScheduleFailureReason, CalendarWindowType, CalendarWindow, WorkOrderTask, ScheduledTask, UnscheduledTask, SchedulingResult, RushRequest, MaterialsAvailabilityProvider, ToolingAvailabilityProvider, SkillsAvailabilityProvider, _AlwaysAvailable, ProductionSchedulingService
- Functions: _require_tzaware, _overlaps, _priority_rank

### backend/src/sensei/services/production/productionization.py
- Size: 37174 bytes
- Lines: 1148
- Classes: EntityType, ImportStatus, ValidationResult, PageRequest, PageResponse, FilterSpec, GLAccountModel, OpeningBalanceModel, SupplierModel, CustomerModel, InventoryItemModel, InventoryLevelModel, ImportBatch, ImportValidation, AuditEvent, Repository, ProductionizationService
- Functions: _utcnow, _norm_roles, _require_any

### backend/src/sensei/services/production/scheduling_maintenance_sync.py
- Size: 6576 bytes
- Lines: 183
- Classes: MaintenanceSyncSummary, SchedulingMaintenanceSyncService
- Functions: _require_tzaware, _overlaps

### backend/src/sensei/services/production/shift_handover_tier_meetings.py
- Size: 13792 bytes
- Lines: 427
- Classes: HandoverSeverity, TierLevel, AgendaItemType, ShiftHandoverNote, TierMeetingAgendaItem, TierMeetingAgenda, EscalationEvent, ShiftHandoverTierMeetingService
- Functions: _require_tzaware, _default_chain, _severity_from_status

### backend/src/sensei/services/production/spc_scrap_rework.py
- Size: 35941 bytes
- Lines: 1096
- Classes: ControlChartType, ViolationType, ScrapReason, ReworkReason, DispositionType, AuditEvent, ControlChart, SPCDataPoint, ControlViolation, ScrapRecord, ReworkRecord, COPQSummary, AccountingLedgerProvider, NCProvider, SPCScrapReworkService
- Functions: _norm_roles, _utcnow, _require_any

### backend/src/sensei/services/production/standard_work_evolution.py
- Size: 14623 bytes
- Lines: 415
- Classes: KPIImpact, EvolutionDecision, AutonomousStandardWorkEvolutionService
- Functions: None

### backend/src/sensei/services/production/standard_work_evolution_worker.py
- Size: 2784 bytes
- Lines: 93
- Classes: StandardWorkEvolutionRunResult, StandardWorkEvolutionJobRunner
- Functions: None

### backend/src/sensei/services/production/wms_integration.py
- Size: 57793 bytes
- Lines: 1723
- Classes: LocationType, InventoryStatus, TransactionType, PickStrategy, CycleCountPriority, ShipmentStatus, WarehouseLocation, WarehouseZone, InventoryRecord, InventoryTransaction, PickTask, PutawayTask, CycleCount, GoodsReceipt, GoodsReceiptLine, Shipment, PackingListLine, StockLevel, WMSIntegrationService
- Functions: create_wms_service

### backend/src/sensei/services/quality/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/quality/audit_evidence.py
- Size: 10450 bytes
- Lines: 330
- Classes: EvidenceType, PackageStatus, EvidenceRecord, AuditPackage, AuditEvidenceService
- Functions: _norm_roles, _utcnow, _compute_hash, _sign_data

### backend/src/sensei/services/quality/audit_trail_timeline.py
- Size: 35719 bytes
- Lines: 1112
- Classes: ChangeType, EntityType, FieldType, RelationshipType, AccessLevel, FieldChange, RelatedEntity, AuditEntry, TimelineGroup, Timeline, TimelineFilter, TimelineConfig, DiffResult, AuditTrailTimelineService
- Functions: get_audit_trail_service, reset_audit_trail_service

### backend/src/sensei/services/quality/capa_workflow.py
- Size: 41087 bytes
- Lines: 1285
- Classes: NCType, NCSeverity, CAPAType, CAPAStatus, CAPAPriority, ActionStatus, ClosureGateType, LinkType, NonConformance, RootCauseAnalysis, CorrectiveAction, ClosureGate, EntityLink, EffectivenessCheck, CAPA, CAPACreationResult, ClosureCheckResult, RecurrenceCheckResult, CAPAConfig, CAPAWorkflowIntegrationService
- Functions: get_capa_workflow_service, reset_capa_workflow_service

### backend/src/sensei/services/quality/change_control.py
- Size: 33911 bytes
- Lines: 1028
- Classes: ChangeType, ChangeStatus, ChangeRisk, ChangeImpact, ApprovalDecision, ConfigValue, ChangeApproval, ImpactAssessment, ChangeAuditEntry, ChangeRequest, ApprovalPolicy, ConfigSnapshot, ChangeControlService
- Functions: None

### backend/src/sensei/services/quality/npi_risk_register.py
- Size: 46401 bytes
- Lines: 1356
- Classes: NPIRiskCategory, RiskPhase, RiskPriority, MitigationStatus, ReviewStatus, MitigationAction, RiskReview, NPIRisk, RiskTemplate, HeatMapCell, NPIRiskRegisterService
- Functions: None

### backend/src/sensei/services/quality/npi_stage_gates.py
- Size: 35314 bytes
- Lines: 1003
- Classes: NPIStage, ArtifactType, ArtifactStatus, GateDecision, TransitionBlockReason, NPIArtifact, GateReview, TransitionResult, NPIProject, StageRequirements, NPIStageGatesService
- Functions: None

### backend/src/sensei/services/quality/qms_quality.py
- Size: 56276 bytes
- Lines: 1507
- Classes: QMSDocumentType, QMSDocumentStatus, SignatureRole, ExternalDocStatus, KPITrend, SCARStatus, AuditType, AuditStatus, FindingSeverity, FindingStatus, RiskType, RiskStatus, MitigationStatus, GaugeStatus, CalibrationStatus, ComplaintStatus, ElectronicSignature, QMSDocumentRevision, QMSDocument, ExternalDocument
- Functions: create_qms_quality_service

### backend/src/sensei/services/quality/quality_certification_gate.py
- Size: 4123 bytes
- Lines: 123
- Classes: CertificationCheckResult, QualityCertificationGate
- Functions: get_quality_certification_gate

### backend/src/sensei/services/readiness_checklists.py
- Size: 42745 bytes
- Lines: 1179
- Classes: ChecklistType, ChecklistStatus, ItemStatus, ItemPriority, PPAPLevel, ChecklistItemDefinition, ChecklistItem, ChecklistSection, Checklist, ChecklistTemplate, ReadinessChecklistsService
- Functions: None

### backend/src/sensei/services/runbooks.py
- Size: 37670 bytes
- Lines: 1065
- Classes: RunbookCategory, RunbookSeverity, StepType, RunbookStatus, RunbookStep, DecisionBranch, RunbookVersion, RunbookExecution, Runbook, RunbookTemplate, RunbooksService
- Functions: None

### backend/src/sensei/services/sales/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/sales/multi_agent_rfq.py
- Size: 59339 bytes
- Lines: 1560
- Classes: AgentType, AnalysisCategory, RiskCategory, DebateOutcome, Severity, DFMIssueType, RFQSpec, DFMIssue, PriceAnalysis, RiskScore, AgentFinding, AgentPosition, DebateResult, ComprehensiveAnalysis, AgentProtocol, BaseAgent, TechnicalAgent, CommercialAgent, RiskAgent, NegotiatorAgent
- Functions: create_rfq_analyzer

### backend/src/sensei/services/sales/predictive_win_loss.py
- Size: 39429 bytes
- Lines: 1124
- Classes: PredictionOutcome, FeatureCategory, ContributionDirection, ExplainerType, Feature, FeatureContribution, ConfidenceInterval, CounterfactualScenario, PredictionResult, HistoricalRFQ, FeatureEngineer, SHAPExplainer, LIMEExplainer, ConfidenceIntervalCalculator, CounterfactualAnalyzer, WinLossPredictionModel, PredictiveWinLossEngine
- Functions: create_win_loss_predictor

### backend/src/sensei/services/sales/quote_approval_time_tracking.py
- Size: 33623 bytes
- Lines: 1004
- Classes: ApprovalDecision, ApprovalReason, ApprovalSessionStatus, ApprovalCriterionStatus, ApprovalCriterion, QuoteApprovalContext, ApprovalSession, ApprovalAlert, ApproverPerformance, QuickApprovalOption, QuoteApprovalTimeTrackingService
- Functions: get_quote_approval_service, reset_quote_approval_service

### backend/src/sensei/services/sales/quote_quality.py
- Size: 36306 bytes
- Lines: 878
- Classes: CheckSeverity, CheckCategory, CheckResult, QualityCheckItem, QualityCheckResult, QuoteData, CheckConfig, QuoteQualityService
- Functions: check_quote_for_release, get_blocking_issues, get_warnings

### backend/src/sensei/services/sales/rfq_completeness.py
- Size: 17738 bytes
- Lines: 514
- Classes: FieldCategory, MissingField, CompletenessResult, RFQCompletenessService
- Functions: None

### backend/src/sensei/services/sales/rfq_time_tracking.py
- Size: 42231 bytes
- Lines: 1202
- Classes: TaskType, TaskSessionStatus, PerformanceLevel, TaskTarget, PauseRecord, TaskSession, TimeAlert, TaskPerformanceStats, UserEfficiencyMetrics, DailyTimeBreakdown, RFQTimeTrackingService
- Functions: get_rfq_time_tracking_service, reset_rfq_time_tracking_service

### backend/src/sensei/services/sales/smart_supplier_matchmaker.py
- Size: 47797 bytes
- Lines: 1394
- Classes: MatchingCriteria, SupplierTier, MatchConfidence, CapabilityType, Capability, PerformanceMetrics, Supplier, RFQRequirement, MatchScore, SupplierMatch, MatchingResult, CapabilityGraph, SemanticMatcher, CriteriaScorer, CapabilityScorer, QualityScorer, DeliveryScorer, PriceScorer, ReliabilityScorer, CertificationScorer
- Functions: create_supplier_matchmaker

### backend/src/sensei/services/saved_views.py
- Size: 36142 bytes
- Lines: 1029
- Classes: SavedViewEntityType, FilterOperator, FilterLogic, DatePreset, SortDirection, ViewVisibility, FilterCondition, SortField, ColumnConfig, SavedView, ViewFilterResult, SavedViewsService
- Functions: build_filter_condition, build_sort_field, build_column_config

### backend/src/sensei/services/segment_views.py
- Size: 38735 bytes
- Lines: 1132
- Classes: FilterOperator, LogicalOperator, FilterCriterion, FilterGroup, SegmentSort, SegmentColumn, LegacySegment, LegacySegmentShare, LegacySegmentUsage, SegmentApplyResult, SegmentViewsService
- Functions: None

### backend/src/sensei/services/segment_views_db.py
- Size: 25360 bytes
- Lines: 808
- Classes: FilterOperator, SegmentViewsService
- Functions: _utcnow, get_segment_views_service

### backend/src/sensei/services/smart_ingestion.py
- Size: 64941 bytes
- Lines: 1783
- Classes: DocumentType, IngestionStatus, ExtractionConfidence, EntityType, FieldType, ExtractedField, ExtractedEntity, DocumentMetadata, OCRResult, OCRPage, OCRWord, OCRTable, EmailContent, EmailAttachment, IngestionJob, IngestionConfig, IngestionStats, FieldExtractor, EntityBuilder, SmartIngestionService
- Functions: _utcnow, detect_document_type, calculate_checksum, normalize_text, parse_date, parse_number, confidence_to_enum, extract_company_from_email, extract_name_from_email, extract_text_from_document, _extract_pdf_text, _extract_image_text

### backend/src/sensei/services/stale_detection.py
- Size: 37088 bytes
- Lines: 934
- Classes: EntityType, StaleReason, StaleSeverity, StaleThreshold, StaleEntity, StaleDetectionResult, StaleDetectionService, StaleDetectionJobRunner
- Functions: None

### backend/src/sensei/services/supply_chain/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/supply_chain/predictive_utility_forecasting.py
- Size: 36740 bytes
- Lines: 1127
- Classes: ResourceType, ForecastHorizon, TrendDirection, SeasonalityType, CapacityStatus, ResourceData, TimeSeriesPoint, SeasonalComponent, TrendComponent, ForecastPoint, ResourceForecast, CapacityPlan, DemandForecast, TimeSeriesDecomposer, DemandForecaster, ResourceForecaster, CapacityPlanner, WhatIfSimulator, PredictiveUtilityEngine
- Functions: create_utility_forecaster

### backend/src/sensei/services/supply_chain/supplier_portal_token.py
- Size: 36679 bytes
- Lines: 1131
- Classes: TokenType, TokenStatus, AccessLevel, SubmissionStatus, FileType, TokenConfig, SupplierContact, PortalToken, UploadedFile, PortalSubmission, TokenAccessLog, NotificationRecord, TokenGenerationResult, ValidationResult, SubmissionResult, SupplierPortalTokenService
- Functions: _utcnow, get_supplier_portal_token_service, reset_supplier_portal_token_service

### backend/src/sensei/services/supply_chain/supply_chain_simulation.py
- Size: 36895 bytes
- Lines: 1040
- Classes: DisruptionType, ImpactSeverity, MitigationStrategy, SimulationStatus, DisruptionScenario, SupplyChainNode, RFQSimulationInput, SimulationResult, ImpactAnalysis, MitigationRecommendation, SimulationReport, DisruptionLibrary, MonteCarloSimulator, ImpactAnalyzer, MitigationAdvisor, SupplyChainSimulator
- Functions: get_supply_chain_simulator, create_supply_chain_simulator

### backend/src/sensei/services/support_inbox.py
- Size: 31312 bytes
- Lines: 962
- Classes: TicketPriority, TicketStatus, TicketCategory, FeedbackType, RoutingTarget, TicketComment, TicketAttachment, RoutingDecision, SupportTicket, UserFeedback, RoutingRule, A3LiteRecord, InboxStats, SupportInboxService
- Functions: None

### backend/src/sensei/services/utils/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/services/utils/chaos_testing.py
- Size: 42394 bytes
- Lines: 1145
- Classes: FailureType, ComponentType, TestStatus, DegradationLevel, CircuitState, FailureScenario, JobRetryTest, DegradationBehavior, DegradationTest, CircuitBreakerState, CircuitBreakerTest, ChaosTestRun, RecoveryMetrics, ChaosTestSummary, ChaosTestingService
- Functions: get_chaos_testing_service, reset_chaos_testing_service

### backend/src/sensei/services/utils/csv_export.py
- Size: 23237 bytes
- Lines: 695
- Classes: ExportableEntityType, ExportFormat, ExportStatus, ColumnConfig, ExportConfig, ExportResult, ExportTemplate, CSVExportService
- Functions: None

### backend/src/sensei/services/utils/csv_import.py
- Size: 40981 bytes
- Lines: 1231
- Classes: ImportEntityType, ImportStatus, RowStatus, DuplicateAction, FieldMappingType, FieldMapping, ValidationError, ImportRowResult, ImportJobResult, DuplicateCandidate, ImportConfig, CSVImportService
- Functions: None

### backend/src/sensei/services/utils/digest_export.py
- Size: 56465 bytes
- Lines: 1701
- Classes: DigestType, DigestFrequency, DigestDeliveryChannel, DigestStatus, DigestFormat, WeekDay, DigestSchedule, DigestRecipient, DigestSection, TodayDigestContent, WeekInReviewContent, ObeyaDigestContent, DigestConfiguration, GeneratedDigest, DigestJob, DigestDeliveryResult, DigestExportService
- Functions: _build_priorities_section, _build_risks_section, _build_commitments_section, _build_abnormalities_section, _build_lsw_section, _build_metrics_section, _build_pipeline_section, _build_obeya_section, _build_a3_section, create_daily_today_schedule, create_weekly_review_schedule, create_monthly_summary_schedule, create_email_recipient, create_in_app_recipient

### backend/src/sensei/services/utils/i18n_backend.py
- Size: 30429 bytes
- Lines: 819
- Classes: Locale, TranslationNamespace, PluralCategory, TranslationKey, MissingTranslation, LocaleConfig, TranslationExport, I18nBackendService
- Functions: None

### backend/src/sensei/services/utils/industrial_ux.py
- Size: 11013 bytes
- Lines: 361
- Classes: ThemeMode, ScanResultType, VoiceNoteStatus, SyncQueueStatus, ThemeConfig, ScanResult, VoiceNote, SyncQueueItem, IndustrialUXService
- Functions: _utcnow

### backend/src/sensei/services/utils/integration_tests.py
- Size: 49213 bytes
- Lines: 1462
- Classes: TestResult, TestCategory, TestPriority, TestStep, TestContext, IntegrationTest, TestExecution, TestSuite, IntegrationTestService
- Functions: None

### backend/src/sensei/services/utils/job_health.py
- Size: 35092 bytes
- Lines: 1061
- Classes: JobType, JobStatus, JobPriority, HealthStatus, JobDefinition, JobExecution, Worker, Queue, JobMetrics, HealthCheck, Alert, JobHealthService
- Functions: None

### backend/src/sensei/services/utils/job_idempotency.py
- Size: 33098 bytes
- Lines: 1045
- Classes: JobStatus, JobType, LockStatus, RetryStrategy, IdempotencyKey, JobLock, RetryConfig, JobRecord, JobResult, JobExecutionStats, JobIdempotencyService
- Functions: _utcnow, create_pdf_idempotency_key, create_email_idempotency_key, create_notification_idempotency_key, create_stale_detection_idempotency_key

### backend/src/sensei/services/utils/locale_formats.py
- Size: 27527 bytes
- Lines: 845
- Classes: Locale, Currency, DateFormat, TimeFormat, NumberFormat, CurrencyInfo, LocaleConfig, FormattedValue, LocaleFormatResult, LocaleFormatsService
- Functions: None

### backend/src/sensei/services/utils/pdf_generation.py
- Size: 41742 bytes
- Lines: 1225
- Classes: PDFDocumentType, PDFLanguage, PDFBrandTemplate, PDFStatus, WatermarkType, BrandingConfig, WatermarkConfig, PDFGenerationOptions, PDFSection, PDFAttachment, GeneratedPDF, QuotePDFData, QualificationPDFData, TodaySnapshotPDFData, ObeyaSnapshotPDFData, WeekInReviewPDFData, EightDReportPDFData, PDFGenerationRequest, PDFTemplate, PDFGenerationService
- Functions: _utcnow, get_pdf_generation_service, reset_pdf_generation_service

### backend/src/sensei/services/utils/ui_backend_integration.py
- Size: 44665 bytes
- Lines: 1208
- Classes: ErrorCategory, RecoveryAction, FieldType, ConnectionState, ErrorMapping, SchemaField, ValidationSchema, ActionAuditEntry, ConnectionHealthStatus, ErrorMappingService, ValidationSchemaExportService, ActionAuditService, ConnectionHealthService, UIBackendIntegration
- Functions: create_ui_backend_integration, create_error_mapping_service, create_schema_export_service, create_action_audit_service, create_connection_health_service

### backend/src/sensei/services/utils/uiux_verification.py
- Size: 24544 bytes
- Lines: 761
- Classes: Breakpoint, DeviceType, AccessibilityLevel, TypographyIssue, LayoutIssue, AccessibilityIssue, InteractionMetrics, AuditReport, UIUXVerificationService
- Functions: _utcnow

### backend/src/sensei/services/virtual_routing.py
- Size: 35432 bytes
- Lines: 1010
- Classes: OperationType, CostBasis, RoutingSource, VirtualOperation, VirtualRouting, RoutingTemplate, VirtualRoutingService
- Functions: None

### backend/src/sensei/services/whatif_simulation.py
- Size: 32017 bytes
- Lines: 920
- Classes: SimulationVariableType, AdjustmentType, ComparisonType, VariableAdjustment, QuoteLineItemData, QuoteData, SimulationScenario, SimulatedLineItem, SimulationResult, ScenarioComparison, WhatIfSimulationService
- Functions: None

### backend/src/sensei/tasks/__init__.py
- Size: 0 bytes
- Lines: 0
- Classes: None
- Functions: None

### backend/src/sensei/tasks/ml_tasks.py
- Size: 7507 bytes
- Lines: 240
- Classes: None
- Functions: run_model_training, check_drift_and_retrain, scheduled_retrain_all, force_model_retrain

### backend/tests/__init__.py
- Size: 35 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/api/__init__.py
- Size: 32 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/api/test_auth.py
- Size: 26490 bytes
- Lines: 743
- Classes: TestRequestSchemas, TestLoginEndpoint, TestRefreshEndpoint, TestPasswordResetEndpoints, TestEmailVerificationEndpoint, TestRequestValidation
- Functions: None

### backend/tests/api/test_deps.py
- Size: 21732 bytes
- Lines: 655
- Classes: TestGetTokenData, TestGetOptionalTokenData, TestGetCurrentUser, TestGetCurrentActiveUser, TestGetCurrentSuperuser, TestPermissionChecker, TestRoleChecker, TestRateLimiter, TestPaginationParams, TestCorrelationId
- Functions: None

### backend/tests/api/test_exceptions.py
- Size: 19561 bytes
- Lines: 600
- Classes: TestSenseiException, TestNotFoundError, TestConflictError, TestBadRequestError, TestUnauthorizedError, TestForbiddenError, TestUnprocessableEntityError, TestRateLimitError, TestServiceUnavailableError, TestBusinessRuleViolationError, TestStateTransitionError, TestApprovalRequiredError, TestFileOperationError, TestExternalServiceError, TestExceptionHandlerIntegration, TestValidationExceptionHandler, TestIntegrityErrorHandler, TestHTTPExceptionHandler
- Functions: None

### backend/tests/api/test_repository.py
- Size: 31223 bytes
- Lines: 908
- Classes: MockModel, TestGetById, TestGetByIdOrRaise, TestGetByIds, TestGetAll, TestGetPaginated, TestExists, TestCount, TestCreate, TestCreateMany, TestUpdate, TestUpdateOrRaise, TestDelete, TestDeleteOrRaise, TestDeleteMany, TestRestore, TestFilterBuilder, TestFindOneBy, TestFindAllBy, TestRepositoryConfiguration
- Functions: mock_db, repository, sample_entity

### backend/tests/api/test_schemas.py
- Size: 19647 bytes
- Lines: 689
- Classes: TestAPIResponse, TestPaginationMeta, TestPaginatedResponse, TestErrorResponse, TestValidationErrorResponse, TestIDRequests, TestSortOrder, TestSearchRequest, TestFilterOperator, TestFilterRequest, TestAuditInfo, TestEntityMeta, TestStatusUpdateRequest, TestArchiveRequest, TestAttachmentInfo, TestHealthStatus, TestServiceStatus, TestPermissionInfo, TestBulkOperationResult, TestExportRequest
- Functions: None

### backend/tests/api/test_utils.py
- Size: 27014 bytes
- Lines: 880
- Classes: TestParseSortParam, TestParseFilterParam, TestParseFilterValue, TestBuildResponse, TestBuildPaginatedResponse, TestBuildCreatedResponse, TestBuildUpdatedResponse, TestBuildDeletedResponse, TestModelToDict, TestModelsToDict, TestApplyPartialUpdate, TestValidateFileExtension, TestValidateFileSize, TestGenerateUniqueFilename, TestGetContentType, TestValidateUuid, TestValidateUuids, TestIsValidEmail, TestNowUtc, TestParseDatetime
- Functions: create_mock_model

### backend/tests/api/v1/__init__.py
- Size: 29 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/api/v1/test_a3.py
- Size: 28573 bytes
- Lines: 818
- Classes: TestA3CRUD, TestA3Workflow, TestA3Sections, TestA3Queries
- Functions: mock_db, mock_user, make_result, create_mock_a3, create_mock_section

### backend/tests/api/v1/test_accounts.py
- Size: 28938 bytes
- Lines: 866
- Classes: TestAccountToResponse, TestAccountToListResponse, TestListAccounts, TestCreateAccount, TestGetAccount, TestUpdateAccount, TestDeleteAccount, TestRestoreAccount, TestEdgeCases
- Functions: mock_user, mock_superuser, sample_account, mock_db

### backend/tests/api/v1/test_analytics_gaps.py
- Size: 4528 bytes
- Lines: 114
- Classes: None
- Functions: app

### backend/tests/api/v1/test_andon.py
- Size: 20888 bytes
- Lines: 700
- Classes: None
- Functions: make_result, make_db, make_user

### backend/tests/api/v1/test_andon_escalation.py
- Size: 17627 bytes
- Lines: 543
- Classes: TestCheckEscalationsEndpoint, TestDetectPatternsEndpoint, TestPatternSummaryEndpoint, TestGenerateA3Endpoint, TestLinkEventsEndpoint, TestThresholdsEndpoints, TestReferenceDataEndpoints, TestValidation
- Functions: base_datetime, sample_events, sample_stations

### backend/tests/api/v1/test_attachments.py
- Size: 20370 bytes
- Lines: 583
- Classes: TestAttachmentCRUD, TestAttachmentVersions, TestAttachmentQueries
- Functions: mock_user, mock_db

### backend/tests/api/v1/test_audit_logs.py
- Size: 15247 bytes
- Lines: 474
- Classes: TestAuditLogRetrieval, TestAuditTrails, TestSpecializedQueries, TestAuditSummary
- Functions: mock_user, mock_db

### backend/tests/api/v1/test_chaos_testing.py
- Size: 27518 bytes
- Lines: 829
- Classes: TestScenarioEndpoints, TestFailureInjectionEndpoints, TestJobRetryEndpoints, TestDegradationEndpoints, TestCircuitBreakerEndpoints, TestTestRunEndpoints, TestRecoveryMetricsEndpoints, TestSummaryEndpoint, TestMaintenanceEndpoint
- Functions: client, reset_service

### backend/tests/api/v1/test_common_thread.py
- Size: 2950 bytes
- Lines: 99
- Classes: None
- Functions: None

### backend/tests/api/v1/test_conditions.py
- Size: 37513 bytes
- Lines: 1067
- Classes: TestTemplateEndpoints, TestAppliedConditionEndpoints, TestConditionSetEndpoints, TestStatisticsEndpoints, TestMetadataEndpoints, TestErrorHandling
- Functions: anyio_backend, entity_id, user_id

### backend/tests/api/v1/test_context_bus.py
- Size: 4062 bytes
- Lines: 134
- Classes: None
- Functions: None

### backend/tests/api/v1/test_ctq.py
- Size: 21763 bytes
- Lines: 603
- Classes: TestCTQCRUD, TestCTQWorkflow, TestCTQMeasurements, TestCTQQueries
- Functions: mock_db, mock_user, make_result, create_mock_ctq, create_mock_measurement

### backend/tests/api/v1/test_data_lineage.py
- Size: 2786 bytes
- Lines: 91
- Classes: None
- Functions: None

### backend/tests/api/v1/test_dev_e2e.py
- Size: 3277 bytes
- Lines: 90
- Classes: None
- Functions: None

### backend/tests/api/v1/test_disaster_recovery_drill.py
- Size: 22592 bytes
- Lines: 689
- Classes: TestTargetEndpoints, TestConfigurationEndpoints, TestScheduleEndpoints, TestExecutionEndpoints, TestReportingEndpoints, TestEnumerationEndpoints, TestMaintenanceEndpoints
- Functions: client

### backend/tests/api/v1/test_escalation_policy.py
- Size: 17293 bytes
- Lines: 492
- Classes: TestPolicyEndpoints, TestThresholdEndpoints, TestDetectionEndpoints, TestFullScanEndpoint, TestReferenceDataEndpoints, TestResponseStructure
- Functions: reference_time, sample_approval, sample_risk, sample_andon

### backend/tests/api/v1/test_exceptions.py
- Size: 19117 bytes
- Lines: 541
- Classes: TestGetExceptions, TestCriticalExceptions, TestSummary, TestNavigationBadges, TestTrends, TestGetByCategory, TestCreateException, TestStatusChanges, TestErrorCases, TestOverdueExceptions, TestEscalatedExceptions
- Functions: app, client, mock_aggregator, sample_exceptions

### backend/tests/api/v1/test_executive_intel.py
- Size: 3218 bytes
- Lines: 93
- Classes: _StubUser
- Functions: make_db

### backend/tests/api/v1/test_gm_onboarding.py
- Size: 13378 bytes
- Lines: 402
- Classes: TestStartOnboarding, TestGetProgress, TestGetSummary, TestStepManagement, TestDashboardTour, TestKeyMetrics, TestFirstActions, TestWorkflowChecklist, TestReset
- Functions: app, client, mock_service

### backend/tests/api/v1/test_kanban.py
- Size: 30407 bytes
- Lines: 992
- Classes: None
- Functions: make_result, make_db, make_user

### backend/tests/api/v1/test_kpi.py
- Size: 28301 bytes
- Lines: 834
- Classes: TestDefinitionEndpoints, TestValueEndpoints, TestCalculationEndpoints, TestTrendEndpoints, TestDashboardEndpoints, TestMetadataEndpoints, TestIntegration, TestMudaNudges
- Functions: client, reset_service

### backend/tests/api/v1/test_learning.py
- Size: 33987 bytes
- Lines: 970
- Classes: TestLearningModules, TestSocraticPedagogyRAG, TestLearningUnits, TestUserProgress, TestAssessments, TestLearningPaths
- Functions: mock_user, mock_db

### backend/tests/api/v1/test_lsw.py
- Size: 28348 bytes
- Lines: 801
- Classes: TestTemplateEndpoints, TestChecklistGeneration, TestItemActions, TestSubItems, TestStatusEndpoints, TestAnalytics, TestMetadata, TestIntegration
- Functions: client, reset_service

### backend/tests/api/v1/test_notification_triggers.py
- Size: 25679 bytes
- Lines: 756
- Classes: TestListEndpoints, TestGetTrigger, TestUpdateTrigger, TestEnableDisable, TestEvaluateTriggers, TestSnooze, TestAcknowledge, TestClearSnooze, TestGetSnoozeSettings, TestIntegration
- Functions: app, client, now, user_id, reset_service

### backend/tests/api/v1/test_obeya.py
- Size: 27017 bytes
- Lines: 773
- Classes: TestObeyaItemCRUD, TestObeyaItemWorkflow, TestObeyaComments, TestObeyaQueries
- Functions: mock_user, mock_db, sample_item_data, create_mock_item

### backend/tests/api/v1/test_opportunities.py
- Size: 45555 bytes
- Lines: 1353
- Classes: TestOpportunityNumberGeneration, TestStageProbabilities, TestListOpportunities, TestCreateOpportunity, TestGetOpportunity, TestUpdateOpportunity, TestDeleteOpportunity, TestStageWorkflow, TestOpportunityNotes, TestPipelineAndForecasting, TestHelperFunctions, TestEdgeCases
- Functions: mock_user, mock_superuser, account_id, primary_contact_id, sample_opportunity, sample_note

### backend/tests/api/v1/test_production_cells.py
- Size: 55882 bytes
- Lines: 1636
- Classes: TestCellConversion, TestPerformanceConversion, TestListProductionCells, TestCreateProductionCell, TestGetProductionCell, TestUpdateProductionCell, TestDeleteProductionCell, TestRestoreProductionCell, TestSetCellStatus, TestUpdateOperators, TestUpdateOutput, TestResetShift, TestGetCellStats, TestListCellPerformances, TestCreateCellPerformance, TestGetCellPerformance, TestUpdateCellPerformance, TestDeleteCellPerformance, TestGetCellOEETrend, TestProductionCellSchemaValidation
- Functions: mock_db, mock_user, sample_cell, sample_cell_string_enums, sample_performance, sample_performance_string_enums

### backend/tests/api/v1/test_products.py
- Size: 38225 bytes
- Lines: 1050
- Classes: TestProductToResponse, TestBOMItemToResponse, TestRoutingToResponse, TestListProducts, TestCreateProduct, TestGetProduct, TestUpdateProduct, TestDeleteProduct, TestCreateNewRevision, TestBOMEndpoints, TestRoutingEndpoints, TestProductStats
- Functions: sample_product, sample_bom_item, sample_routing, mock_current_user

### backend/tests/api/v1/test_project_management.py
- Size: 16273 bytes
- Lines: 452
- Classes: None
- Functions: None

### backend/tests/api/v1/test_quality.py
- Size: 22436 bytes
- Lines: 730
- Classes: None
- Functions: make_result, make_db

### backend/tests/api/v1/test_quote_approval_time_tracking.py
- Size: 21521 bytes
- Lines: 652
- Classes: TestStartApprovalSession, TestGetSession, TestGetCountdownStatus, TestMakeDecision, TestQuickApprove, TestUpdateCriterion, TestAbandonSession, TestGetQuoteSessions, TestGetApproverPending, TestGetQuickOptions, TestGetApproverPerformance, TestGetQuoteSummary, TestGetLeaderboard, TestTargets
- Functions: client, reset_service, sample_context, sample_approver_id

### backend/tests/api/v1/test_quote_quality.py
- Size: 26046 bytes
- Lines: 684
- Classes: TestCheckQuoteQuality, TestCheckWithConfig, TestQuickCheck, TestBlockingIssues, TestWarnings, TestCategories, TestSeverities, TestDefaultConfig, TestValidateConfig, TestCheckTypes, TestIntegration, TestEdgeCases
- Functions: client, valid_quote_data, minimal_quote_data

### backend/tests/api/v1/test_quotes.py
- Size: 51765 bytes
- Lines: 1570
- Classes: TestQuoteNumberGeneration, TestNextLineNumber, TestListQuotes, TestCreateQuote, TestGetQuote, TestUpdateQuote, TestDeleteQuote, TestLineItems, TestQuoteWorkflow, TestVersionControl, TestQuoteStats, TestHelperFunctions, TestRecalculation, TestEdgeCases
- Functions: mock_user, mock_superuser, account_id, contact_id, sample_quote, sample_line_item, sample_version

### backend/tests/api/v1/test_rbac_security_audit.py
- Size: 22029 bytes
- Lines: 685
- Classes: TestRoleEndpoints, TestPermissionEndpoints, TestUserRoleEndpoints, TestAuditLogEndpoints, TestAccessPatternEndpoints, TestVerificationEndpoints, TestFindingsEndpoints, TestComplianceReportEndpoint, TestMaintenanceEndpoints, TestValidation
- Functions: client, reset_service, iso_now

### backend/tests/api/v1/test_rfq_time_tracking.py
- Size: 17602 bytes
- Lines: 525
- Classes: TestSessionEndpoints, TestAlertEndpoints, TestTargetEndpoints, TestAnalyticsEndpoints, TestRFQSummaryEndpoints, TestMaintenanceEndpoints
- Functions: app, client, sample_rfq_id, sample_user_id

### backend/tests/api/v1/test_rfqs.py
- Size: 50962 bytes
- Lines: 1543
- Classes: TestRFQNumberGeneration, TestListRFQs, TestCreateRFQ, TestGetRFQ, TestUpdateRFQ, TestDeleteRFQ, TestRFQWorkflow, TestRFQQuestions, TestRFQStats, TestHelperFunctions, TestEdgeCases, TestRFQCompletenessEndpoints
- Functions: mock_user, mock_superuser, account_id, contact_id, sample_rfq, sample_question

### backend/tests/api/v1/test_risk.py
- Size: 28167 bytes
- Lines: 751
- Classes: TestRiskCRUD, TestRiskWorkflow, TestRiskMitigations, TestRiskQueries
- Functions: mock_db, mock_user, make_result, create_mock_risk, create_mock_mitigation

### backend/tests/api/v1/test_saved_views.py
- Size: 24940 bytes
- Lines: 729
- Classes: TestCreateView, TestListViews, TestListSystemViews, TestGetView, TestUpdateView, TestDeleteView, TestDuplicateView, TestPinView, TestPinnedViews, TestDefaultView, TestApplyView, TestReferenceData, TestSavedViewsIntegration
- Functions: app, client, clear_service, user_id

### backend/tests/api/v1/test_search.py
- Size: 24650 bytes
- Lines: 660
- Classes: TestSearchEndpoint, TestQuickSearchEndpoint, TestSuggestionsEndpoint, TestEntityTypesEndpoint, TestStatsEndpoint, TestIndexDocumentEndpoint, TestIndexAccountEndpoint, TestIndexRFQEndpoint, TestIndexQuoteEndpoint, TestIndexTaskEndpoint, TestRemoveDocumentEndpoint, TestClearIndexEndpoint, TestSearchIntegration
- Functions: app, client, clear_service

### backend/tests/api/v1/test_stale_detection.py
- Size: 14165 bytes
- Lines: 415
- Classes: TestStaleDetectionThresholdEndpoints, TestStaleDetectionEndpoints, TestFullScanEndpoint, TestReferenceDataEndpoints, TestResponseStructure
- Functions: reference_time, sample_opportunities, sample_rfqs, sample_tasks

### backend/tests/api/v1/test_standard_work.py
- Size: 31679 bytes
- Lines: 981
- Classes: None
- Functions: make_result, db, current_user

### backend/tests/api/v1/test_state_machines.py
- Size: 11723 bytes
- Lines: 344
- Classes: TestListStateMachines, TestGetStateMachine, TestGetAvailableTransitions, TestCheckTransition, TestGetTransitionRequirements
- Functions: mock_user

### backend/tests/api/v1/test_tasks.py
- Size: 28587 bytes
- Lines: 837
- Classes: TestTaskCRUD, TestTaskWorkflow, TestChecklist, TestTimeTracking, TestTaskComments, TestTaskQueries
- Functions: mock_user, mock_db, sample_task_data, create_mock_task

### backend/tests/api/v1/test_today.py
- Size: 32691 bytes
- Lines: 922
- Classes: TestPriorityEndpoints, TestRiskEndpoints, TestCommitmentEndpoints, TestAbnormalityEndpoints, TestMicroDrillEndpoints, TestLSWSummaryEndpoints, TestQuickMetricsEndpoints, TestTodayScreenEndpoints, TestMetadataEndpoints, TestEdgeCases
- Functions: client, sample_user_id

### backend/tests/api/v1/test_training.py
- Size: 41775 bytes
- Lines: 1204
- Classes: TestSkillCRUD, TestSkillRequirements, TestTrainingCRUD, TestTrainingParticipants, TestUserSkills
- Functions: _utcnow, mock_db, mock_user, sample_skill_data, sample_training_data

### backend/tests/api/v1/test_training_matrix.py
- Size: 11451 bytes
- Lines: 329
- Classes: TestMatrixGeneration, TestGapAnalysis, TestExpirationAlerts, TestUserSummary, TestStationReadiness, TestReferenceData, TestResponseStructures
- Functions: client, reference_date

### backend/tests/api/v1/test_work_centers.py
- Size: 54040 bytes
- Lines: 1569
- Classes: TestWorkCenterConversion, TestStationConversion, TestListWorkCenters, TestCreateWorkCenter, TestGetWorkCenter, TestUpdateWorkCenter, TestDeleteWorkCenter, TestRestoreWorkCenter, TestWorkCenterStats, TestListStations, TestCreateStation, TestGetStation, TestUpdateStation, TestDeleteStation, TestRestoreStation, TestCreateStationDirect, TestWorkCenterSchemaValidation, TestStationSchemaValidation, TestEdgeCases
- Functions: mock_user, mock_superuser, sample_work_center, sample_station, sample_bottleneck_station, mock_db

### backend/tests/api/v1/test_work_orders.py
- Size: 58576 bytes
- Lines: 1642
- Classes: TestWorkOrderConversion, TestOperationConversion, TestListWorkOrders, TestCreateWorkOrder, TestGetWorkOrder, TestUpdateWorkOrder, TestDeleteWorkOrder, TestReleaseWorkOrder, TestStartWorkOrder, TestHoldWorkOrder, TestResumeWorkOrder, TestCompleteWorkOrder, TestCancelWorkOrder, TestCloseWorkOrder, TestListOperations, TestCreateOperation, TestStartOperation, TestCompleteOperation, TestBlockOperation, TestUnblockOperation
- Functions: mock_db, mock_user, sample_work_order, sample_operation

### backend/tests/conftest.py
- Size: 5813 bytes
- Lines: 193
- Classes: None
- Functions: _compile_jsonb_sqlite, _compile_array_sqlite, _compile_uuid_sqlite, test_settings, mock_db_session, mock_redis_client, mock_storage_client, sample_file_content, sample_pdf_content, sample_user_data, sample_rfq_data, sample_quote_data

### backend/tests/core/__init__.py
- Size: 40 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/core/test_auth.py
- Size: 33194 bytes
- Lines: 900
- Classes: TestAuthenticationExceptions, TestAuthServiceUnit, TestAuthFlows
- Functions: None

### backend/tests/core/test_config.py
- Size: 10538 bytes
- Lines: 261
- Classes: TestSettingsValidation, TestEnvironmentDetection, TestDefaultValues, TestInvalidEnvironmentValues
- Functions: None

### backend/tests/core/test_redis.py
- Size: 5804 bytes
- Lines: 183
- Classes: TestCacheGet, TestCacheSet, TestCacheDelete, TestCacheExists, TestCheckRedisConnection
- Functions: None

### backend/tests/core/test_security.py
- Size: 25137 bytes
- Lines: 714
- Classes: TestPasswordHashing, TestJWTTokens, TestTOTP, TestBackupCodes, TestSecureTokens, TestRateLimitingKeys, TestTokenModels
- Functions: None

### backend/tests/core/test_storage.py
- Size: 11887 bytes
- Lines: 348
- Classes: TestGenerateFileKey, TestComputeFileHash, TestUploadFile, TestDownloadFile, TestDeleteFile, TestGeneratePresignedUrl, TestListFiles, TestCheckStorageConnection
- Functions: None

### backend/tests/e2e/test_ai_reasoning.py
- Size: 12871 bytes
- Lines: 389
- Classes: TestHybridSearchPrecision, TestContinuousLearningLoop, TestPredictiveAccuracy, TestAnomalyDetection, TestRBACEnforcement
- Functions: svc

### backend/tests/e2e/test_ceo_control_plane.py
- Size: 12626 bytes
- Lines: 352
- Classes: TestNL2SQLStressTest, TestEmployeeIntelligence, TestSkillMatrix, TestExecutiveWarRoom, TestRBACEnforcement
- Functions: svc

### backend/tests/e2e/test_factory_launchpad_e2e.py
- Size: 53262 bytes
- Lines: 1510
- Classes: E2EMaturityLevel, E2EFeatureModule, E2EVerificationStatus, SiteData, UIElementState, VerificationResult, LevelUpEvent, FactoryLaunchpadE2EService, TestE2EEnums, TestMaturityFeatureMapping, TestSiteRegistration, TestMaturityToggleVerification, TestLevelUpEvent, TestRehearsalFidelity, TestFullVerificationSuite, TestRBACEnforcement, TestDataClasses
- Functions: create_factory_launchpad_e2e_service, e2e_service, test_site

### backend/tests/e2e/test_feature_matrix.py
- Size: 53256 bytes
- Lines: 1485
- Classes: FeatureCategory, FeatureStatus, VerificationLevel, FeatureDefinition, VerificationResult, CategoryVerification, FeatureMatrixVerificationService, TestFeatureEnums, TestFeatureDefinitions, TestInfrastructureFeatures, TestCRMFeatures, TestRFQFeatures, TestQuotingFeatures, TestManagementFeatures, TestProductionFeatures, TestQualityFeatures, TestUXFeatures, TestKnowledgeFeatures, TestOpsFeatures, TestCategoryVerification
- Functions: create_feature_matrix_verification_service, service

### backend/tests/e2e/test_infrastructure_resilience.py
- Size: 11447 bytes
- Lines: 313
- Classes: TestONNXInferenceLatency, TestMemoryThrottling, TestModelWarmup, TestDBAutonomy, TestHealthWatchdog, TestS3LocalConsistency, TestBackupRestoreFireDrill, TestRBACEnforcement
- Functions: svc

### backend/tests/e2e/test_persona_management.py
- Size: 8151 bytes
- Lines: 224
- Classes: TestCEOAccountCreation, TestGlobalPersonaVerification, TestAuditLogAttribution, TestAllPersonaRoles, TestFeatureAccessControl
- Functions: svc

### backend/tests/e2e/test_uiux_verification.py
- Size: 18557 bytes
- Lines: 543
- Classes: TestTypographyAudit, TestWhitespaceSurfaces, TestDesignTokenAudit, TestBreakpointStressTest, TestSafeAreas, TestContainerMaxWidth, TestMicroInteractions, TestSkeletonTransitions, TestHapticFeedback, TestOptimisticUI, TestKeyboardNavigation, TestScreenReaderAudit, TestHitTargetEnforcement, TestComprehensiveAudit, TestRBACEnforcement
- Functions: svc

### backend/tests/functional/test_workflow_gates.py
- Size: 19634 bytes
- Lines: 522
- Classes: TestRFQCompletenessGating, TestQualificationApprovalLogic, TestQuoteVersionImmutability, TestA3ClosureRequirements
- Functions: mock_db_session, data_quality_service

### backend/tests/middleware/__init__.py
- Size: 46 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/middleware/test_middleware.py
- Size: 6641 bytes
- Lines: 203
- Classes: TestCorrelationIdMiddleware, TestTimingMiddleware, TestStructuredLoggingMiddleware, TestMiddlewareIntegration
- Functions: create_test_app

### backend/tests/middleware/test_secure_headers.py
- Size: 29964 bytes
- Lines: 891
- Classes: TestCSPConfig, TestHSTSConfig, TestPermissionsPolicyConfig, TestCacheControlConfig, TestSecureHeadersMiddleware, TestCSPConfiguration, TestHSTSConfiguration, TestOtherHeaderConfiguration, TestHeaderGeneration, TestHeaderOverrides, TestOverrideApplication, TestCSPViolationReporting, TestPresets, TestStatisticsAndValidation, TestEnumValues
- Functions: None

### backend/tests/ml/__init__.py
- Size: 28 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/ml/test_cbm_predictor.py
- Size: 21067 bytes
- Lines: 592
- Classes: MockEquipment, MockMaintenanceRecord, MockConditionReading, TestCBMPredictorInit, TestCriticalThresholdDetection, TestNormalOperationDetection, TestMissingDataHandling, TestResultStructure, TestFeatureExtraction, TestCBMTraining, TestCBMEdgeCases, TestThresholdConfiguration
- Functions: _utcnow, healthy_equipment, aging_equipment, normal_readings, critical_readings, degrading_readings, maintenance_history, temp_model_path

### backend/tests/ml/test_evaluation.py
- Size: 20235 bytes
- Lines: 583
- Classes: TestEvaluationResults, TestModelEvaluatorInit, TestClassifierEvaluation, TestRegressionEvaluation, TestCalibrationAnalysis, TestFairnessMetrics, TestBusinessMetrics, TestModelComparison, TestReportGeneration, TestEdgeCases
- Functions: None

### backend/tests/ml/test_evidence_detector.py
- Size: 21464 bytes
- Lines: 538
- Classes: MockA3Report, TestEvidenceDetectorInit, TestEvidencePatternDetection, TestSectionCompleteness, TestDetectionResults, TestAttachmentCheck, TestEvidenceDetectorTraining, TestEvidenceDetectorLoading, TestBatchAnalysis, TestEdgeCases
- Functions: complete_report, incomplete_report, partial_report, temp_model_path

### backend/tests/ml/test_lesson_recommender.py
- Size: 19920 bytes
- Lines: 594
- Classes: MockLesson, MockLessonCompletion, MockUser, TestLessonRecommenderInit, TestLessonRecommenderTraining, TestLessonRecommenderLoading, TestLessonRecommenderRecommendations, TestRoleMatching, TestSkillsGapDetection, TestBatchRecommendations, TestContentSimilarity
- Functions: _utcnow, sample_lessons, sample_users, sample_completions, temp_model_path

### backend/tests/ml/test_mlops.py
- Size: 23831 bytes
- Lines: 598
- Classes: TestModelStatus, TestModelMetadata, TestModelRegistry, TestModelMonitor, TestABTestManager, TestMLPipeline, TestRollbackScenarios, TestMLOpsEdgeCases
- Functions: _utcnow, temp_registry_path, sample_model_metadata, sample_model_artifacts

### backend/tests/ml/test_safety_gates.py
- Size: 22734 bytes
- Lines: 658
- Classes: TestSafetyCheckStatus, TestSafetyCheckResult, TestSafetyGateResults, TestSafetyGateConfig, TestMLSafetyGatesInit, TestPerformanceChecks, TestFairnessChecks, TestTrainingDataChecks, TestBusinessMetricsChecks, TestInferencePerformanceChecks, TestModelComplexityChecks, TestFullGateCheck, TestRecommendations, TestEdgeCases
- Functions: sample_eval_results, failing_eval_results, sample_training_metadata, sample_inference_metrics

### backend/tests/models/__init__.py
- Size: 35 bytes
- Lines: 4
- Classes: None
- Functions: None

### backend/tests/models/test_a3.py
- Size: 17170 bytes
- Lines: 495
- Classes: TestA3Model, TestA3StatusEnum, TestA3TypeEnum, TestA3PriorityEnum, TestA3SectionModel, TestA3SectionTypeEnum, TestA3SectionOrdering
- Functions: None

### backend/tests/models/test_account.py
- Size: 13675 bytes
- Lines: 327
- Classes: TestAccountModel, TestAccountTypeEnum, TestAccountStatusEnum, TestAccountTierEnum, TestContactModel, TestContactRoleEnum, TestAccountContactModel
- Functions: None

### backend/tests/models/test_andon.py
- Size: 17897 bytes
- Lines: 540
- Classes: TestAndonEventModel, TestAndonEscalationModel, TestAndonRecurrencePatternModel, TestAndonEventRelationships, TestAndonValidation, TestAndonEdgeCases
- Functions: None

### backend/tests/models/test_attachment.py
- Size: 18922 bytes
- Lines: 510
- Classes: TestAttachmentModel, TestAttachmentStatusEnum, TestAttachmentCategoryEnum, TestAttachmentVersionModel
- Functions: None

### backend/tests/models/test_audit_log.py
- Size: 8876 bytes
- Lines: 263
- Classes: TestAuditLogModel, TestAuditActionEnum
- Functions: None

### backend/tests/models/test_base.py
- Size: 6989 bytes
- Lines: 237
- Classes: TestBaseModel, TestTimestampMixin, TestAuditMixin, TestSoftDeleteMixin, TestStatusMixin, TestGenerateULID, TestModelSerialization
- Functions: None

### backend/tests/models/test_ctq.py
- Size: 14666 bytes
- Lines: 390
- Classes: TestCTQModel, TestCTQCategoryEnum, TestCTQStatusEnum, TestCTQPriorityEnum, TestCTQMeasurementModel, TestMeasurementResultEnum
- Functions: None

### backend/tests/models/test_kanban.py
- Size: 16328 bytes
- Lines: 547
- Classes: TestKanbanBoardModel, TestKanbanCardModel, TestKanbanCardHistoryModel, TestKanbanRelationships, TestKanbanValidation, TestKanbanEdgeCases
- Functions: None

### backend/tests/models/test_learning.py
- Size: 15830 bytes
- Lines: 400
- Classes: TestLearningUnitModel, TestLearningStatusEnum, TestDifficultyLevelEnum, TestContentTypeEnum, TestLearningCategoryEnum, TestLearningModuleModel, TestUserLearningProgressModel, TestProgressStatusEnum
- Functions: None

### backend/tests/models/test_obeya.py
- Size: 12880 bytes
- Lines: 359
- Classes: TestObeyaItemModel, TestObeyaCategoryEnum, TestObeyaStatusEnum, TestObeyaPriorityEnum, TestObeyaBoardEnum, TestObeyaCommentModel
- Functions: None

### backend/tests/models/test_opportunity_rfq.py
- Size: 19479 bytes
- Lines: 579
- Classes: TestOpportunityModel, TestOpportunityStageEnum, TestOpportunityNoteModel, TestRFQModel, TestRFQStatusEnum, TestRFQQuestionModel, TestRFQAttachmentModel
- Functions: None

### backend/tests/models/test_product.py
- Size: 16516 bytes
- Lines: 532
- Classes: TestProductModel, TestBOMItemModel, TestRoutingModel, TestProductBOMRelationship, TestProductRoutingRelationship, TestProductValidation, TestBOMItemValidation, TestRoutingValidation, TestProductEdgeCases, TestBOMItemEdgeCases, TestRoutingEdgeCases
- Functions: None

### backend/tests/models/test_production.py
- Size: 20142 bytes
- Lines: 602
- Classes: TestProductionCellModel, TestCellPerformanceModel, TestCellPerformanceOEECalculation, TestProductionRelationships, TestProductionValidation, TestProductionEdgeCases
- Functions: None

### backend/tests/models/test_qualification.py
- Size: 11381 bytes
- Lines: 339
- Classes: TestQualificationModel, TestQualificationResultEnum, TestQualificationCriterionModel, TestCriterionCategoryEnum, TestCriterionTypeEnum, TestQualificationScoreModel, TestScoreValueEnum
- Functions: None

### backend/tests/models/test_quality.py
- Size: 30596 bytes
- Lines: 934
- Classes: TestNonConformanceModel, TestCAPAModel, TestCAPAActionModel, TestInspectionPlanModel, TestInspectionRecordModel, TestQualityRelationships, TestQualityValidation, TestQualityEdgeCases
- Functions: None

### backend/tests/models/test_quote.py
- Size: 14701 bytes
- Lines: 426
- Classes: TestQuoteModel, TestQuoteStatusEnum, TestApprovalStatusEnum, TestQuoteVersionModel, TestQuoteLineItemModel, TestLineItemTypeEnum, TestSupplierQuoteModel, TestSupplierQuoteStatusEnum, TestSupplierQuoteItemModel
- Functions: None

### backend/tests/models/test_risk.py
- Size: 18409 bytes
- Lines: 495
- Classes: TestRiskModel, TestRiskCategoryEnum, TestRiskStatusEnum, TestRiskSeverityEnum, TestRiskLikelihoodEnum, TestRiskMitigationModel, TestMitigationStatusEnum
- Functions: None

### backend/tests/models/test_standard_work.py
- Size: 15585 bytes
- Lines: 466
- Classes: TestStandardWorkModel, TestStandardWorkVersionModel, TestStandardWorkRelationships, TestStandardWorkValidation, TestStandardWorkEdgeCases
- Functions: None

### backend/tests/models/test_task.py
- Size: 15706 bytes
- Lines: 457
- Classes: TestTaskModel, TestTaskStatusEnum, TestTaskPriorityEnum, TestTaskTypeEnum, TestTaskCommentModel, TestNotificationModel, TestNotificationTypeEnum, TestNotificationStatusEnum, TestNotificationPriorityEnum, TestNotificationChannelEnum
- Functions: None

### backend/tests/models/test_training.py
- Size: 19746 bytes
- Lines: 635
- Classes: TestSkillModel, TestSkillRequirementModel, TestTrainingModel, TestTrainingParticipantModel, TestUserSkillModel, TestTrainingRelationships, TestTrainingValidation, TestTrainingEdgeCases
- Functions: None

### backend/tests/models/test_user.py
- Size: 14991 bytes
- Lines: 440
- Classes: TestUserModel, TestRoleModel, TestPermissionModel, TestUserRoleModel, TestRolePermissionModel, TestRefreshTokenModel, TestUserStatusEnum, TestRoleTypeEnum
- Functions: None

### backend/tests/models/test_work_center.py
- Size: 12901 bytes
- Lines: 402
- Classes: TestWorkCenterModel, TestStationModel, TestWorkCenterStationRelationship, TestWorkCenterValidation, TestStationValidation, TestWorkCenterEdgeCases, TestStationEdgeCases
- Functions: None

### backend/tests/models/test_work_order.py
- Size: 17888 bytes
- Lines: 528
- Classes: TestWorkOrderModel, TestWorkOrderOperationModel, TestWorkOrderOperationRelationship, TestWorkOrderValidation, TestWorkOrderEdgeCases
- Functions: None

### backend/tests/performance/README.md
- Size: 7027 bytes
- Lines: 235
- Headings: # Performance Load Testing | ## Overview | ## Prerequisites | # macOS | # Linux (Debian/Ubuntu) | # Windows (Chocolatey) | ## Running Tests | ### Today Screen Load Test | # Run with default settings (localhost:8000) | # Run with custom base URL | # Run with custom duration (shorter for quick validation) | # Run with results output to JSON
- First paragraph: This directory contains k6 load testing scripts for the Sensei application.

### backend/tests/performance/load_test_concurrent_approvals.js
- Size: 6939 bytes
- Lines: 238
- Exports: options, setup, teardown

### backend/tests/performance/load_test_search.js
- Size: 5401 bytes
- Lines: 217
- Exports: options, setup, teardown

### backend/tests/performance/load_test_today_screen.js
- Size: 5430 bytes
- Lines: 192
- Exports: options, setup, teardown

### backend/tests/performance/test_backup_restore.py
- Size: 9006 bytes
- Lines: 225
- Classes: TestBackupRestore
- Functions: None

### backend/tests/performance/test_latency.py
- Size: 9865 bytes
- Lines: 267
- Classes: TestTodayScreenLatency
- Functions: None

### backend/tests/performance/test_search_performance.py
- Size: 8351 bytes
- Lines: 217
- Classes: TestSearchPerformance
- Functions: None

### backend/tests/security/test_rbac_verification.py
- Size: 13119 bytes
- Lines: 291
- Classes: Role, Permission, TestRBACVerification
- Functions: None

### backend/tests/services/__init__.py
- Size: 35 bytes
- Lines: 2
- Classes: None
- Functions: None

### backend/tests/services/test_access_review.py
- Size: 27211 bytes
- Lines: 757
- Classes: TestEnums, TestServiceInitialization, TestCampaignManagement, TestUserAccessManagement, TestAttestations, TestReminders, TestViolations, TestAutomaticChecks, TestReporting, TestScheduleManagement, TestCampaignProgress, TestEdgeCases
- Functions: None

### backend/tests/services/test_accounting_ledger.py
- Size: 7366 bytes
- Lines: 213
- Classes: None
- Functions: _roles, test_coa_upsert_and_list_requires_rbac, test_journal_entry_lifecycle_post_and_trial_balance, test_period_close_blocks_unposted_entries_and_reopen_requires_reason, test_multi_currency_posting_and_fx_revaluation_creates_entry

### backend/tests/services/test_accounts_payable.py
- Size: 7949 bytes
- Lines: 221
- Classes: None
- Functions: _setup_minimal_coa, test_pr_must_be_approved_before_po_creation, test_three_way_match_blocks_invoice_without_override, test_invoice_post_and_payment_run_post_to_gl

### backend/tests/services/test_accounts_receivable.py
- Size: 6023 bytes
- Lines: 195
- Classes: None
- Functions: _approved_quote, test_quote_requires_approval_for_sales_order, test_credit_limit_blocks_sales_order_approval, test_credit_limit_override_requires_reason_and_allows_approval, test_end_to_end_invoice_payment_and_aging_and_gl_postings

### backend/tests/services/test_activity_feed.py
- Size: 33361 bytes
- Lines: 1124
- Classes: TestActivityCreation, TestFeedRetrieval, TestReadStatus, TestAggregation, TestSubscriptions, TestDigest, TestEdgeCases
- Functions: service, user_id, target_id

### backend/tests/services/test_advanced_rag.py
- Size: 34606 bytes
- Lines: 1042
- Classes: TestChunk, TestTableChunk, TestImageChunk, TestQueryAnalysis, TestRetrievalResult, TestSemanticChunker, TestHierarchicalChunker, TestQueryAnalyzer, TestBGEReranker, TestLLMReranker, TestInMemoryVectorStore, TestAdvancedRAGService, TestAdvancedRAGIntegration, TestAdvancedRAGEdgeCases, TestAdvancedRAGPerformance
- Functions: run_async

### backend/tests/services/test_ai_content_drafting.py
- Size: 34385 bytes
- Lines: 975
- Classes: TestEnums, TestKnowledgeSource, TestDraftContent, TestA3Context, TestA3SectionDraft, TestA3FullDraft, TestA3SectionDrafting, TestFullA3Drafting, TestDraftManagement, TestKnowledgeBase, TestConfidenceAndWarnings, TestHumanConfirmationWorkflow, TestServiceSingleton, TestEdgeCases
- Functions: reset_service, service, sample_context, sample_a3_request

### backend/tests/services/test_ai_ctq_summarization.py
- Size: 51614 bytes
- Lines: 1472
- Classes: TestSummaryType, TestAnalysisPeriod, TestRiskLevel, TestTrendDirection, TestCapabilityStatus, TestRecommendationType, TestOutputFormat, TestMeasurementData, TestCTQSpec, TestStatisticalSummary, TestTrendAnalysis, TestRiskAssessment, TestRecommendation, TestStatisticalAnalysis, TestCapabilityStatusDetermination, TestTrendAnalysis, TestRiskAssessment, TestRecommendations, TestSummaryGeneration, TestExecutiveSummary
- Functions: None

### backend/tests/services/test_ai_email_drafting.py
- Size: 62594 bytes
- Lines: 1664
- Classes: TestEmailTone, TestEmailPurpose, TestDraftStatus, TestLanguage, TestComplianceCheckType, TestSuggestionType, TestRecipient, TestEmailContext, TestGenerationRequest, TestSubjectTemplates, TestSalutationTemplates, TestClosingTemplates, TestDraftGeneration, TestSubjectGeneration, TestSalutationGeneration, TestContentGeneration, TestSignatureGeneration, TestHTMLConversion, TestDraftManagement, TestComplianceChecks
- Functions: service, service_with_config, sample_recipient, sample_context, sample_request

### backend/tests/services/test_ai_learning_recommendations.py
- Size: 47022 bytes
- Lines: 1429
- Classes: TestRecommendationType, TestRecommendationPriority, TestLearningGoal, TestSkillLevel, TestLearningStyle, TestContextTrigger, TestContentCategory, TestDifficultyLevel, TestUserProfile, TestLearningUnitInfo, TestProgressData, TestSkillAssessment, TestLearningRecommendation, TestSkillGap, TestLearningPath, TestSpacedRepetitionSchedule, TestRecommendationSet, TestServiceInitialization, TestRecommendationGeneration, TestReviewRecommendations
- Functions: service, sample_user_profile, sample_units, sample_progress

### backend/tests/services/test_ai_qualification_advisory.py
- Size: 54168 bytes
- Lines: 1622
- Classes: TestAdvisoryType, TestDecisionRecommendation, TestConfidenceLevel, TestRiskCategory, TestRiskSeverity, TestGapSeverity, TestActionPriority, TestScoringRationale, TestCriterionData, TestScoreData, TestQualificationData, TestScoringRecommendation, TestIdentifiedRisk, TestGap, TestRecommendedAction, TestDecisionSupport, TestBenchmarkResult, TestQualificationAdvisory, TestServiceInitialization, TestScoringRecommendations
- Functions: service, sample_criteria, sample_scores, sample_qualification, sample_rfq_context

### backend/tests/services/test_ai_readiness.py
- Size: 1364 bytes
- Lines: 41
- Classes: None
- Functions: test_model_registry_paths

### backend/tests/services/test_alerting_config.py
- Size: 35096 bytes
- Lines: 1107
- Classes: TestEnums, TestRuleManagement, TestNotificationTargets, TestNotificationRoutes, TestAlertManagement, TestSilenceManagement, TestAlertGrouping, TestHistory, TestValidation, TestSummary, TestIntegration
- Functions: service, sample_condition, sample_rule, sample_target, sample_route

### backend/tests/services/test_analytics_warehouse.py
- Size: 5612 bytes
- Lines: 161
- Classes: TestDailySnapshots, TestDimensionalModeling, TestSnapshotListing
- Functions: svc

### backend/tests/services/test_andon_a3_escalation.py
- Size: 43495 bytes
- Lines: 1323
- Classes: TestThresholdConfiguration, TestRecurrencePatternDetection, TestEscalationEvaluation, TestCheckForEscalations, TestA3TemplateGeneration, TestLinkEventsToA3, TestPatternSummary, TestAndonA3EscalationJobRunner, TestEdgeCases
- Functions: service, base_datetime, sample_events, high_downtime_events, high_cost_events, stations, products

### backend/tests/services/test_audit_evidence.py
- Size: 6096 bytes
- Lines: 188
- Classes: TestEvidenceRecords, TestAuditPackages, TestRoleEnforcement
- Functions: svc

### backend/tests/services/test_audit_trail_timeline.py
- Size: 38105 bytes
- Lines: 1175
- Classes: TestChangeType, TestEntityType, TestFieldType, TestAccessLevel, TestFieldChange, TestRelatedEntity, TestAuditEntry, TestDiffResult, TestServiceInitialization, TestFieldMetadata, TestDiffCalculation, TestRecordCreate, TestRecordUpdate, TestRecordDelete, TestRecordLink, TestRecordAttachment, TestRecordComment, TestRecordApproval, TestRecordRejection, TestRecordEscalation
- Functions: service, user_id, user_name, entity_id

### backend/tests/services/test_automated_feedback_loops.py
- Size: 38436 bytes
- Lines: 1022
- Classes: TestModelVersion, TestUserInfo, TestCorrection, TestInMemoryLearningStore, TestConflictResolver, TestFewShotInjector, TestCorrectionVersionManager, TestFeedbackLoopManager, TestFactory, TestEnums, TestEdgeCases, TestIntegration
- Functions: model_version, user_info, expert_user, correction_metadata, sample_correction, store, feedback_manager

### backend/tests/services/test_autosave_drafts.py
- Size: 26881 bytes
- Lines: 869
- Classes: TestDraftCreation, TestDraftRetrieval, TestAutosave, TestManualSave, TestVersionHistory, TestDraftLifecycle, TestConflictDetection, TestDraftRecovery, TestCleanup, TestStatistics, TestEdgeCases
- Functions: None

### backend/tests/services/test_backup_scheduler.py
- Size: 19961 bytes
- Lines: 551
- Classes: TestBackupSchedulerInitialization, TestSchedulerLifecycle, TestScheduleManagement, TestBackupExecution, TestComplianceMonitoring, TestDisasterRecoveryReadiness, TestForceBackup, TestScheduleHistory
- Functions: mock_backup_service, mock_scheduler, backup_scheduler_service

### backend/tests/services/test_bulk_actions.py
- Size: 35297 bytes
- Lines: 1131
- Classes: TestBulkStatusUpdates, TestBulkOwnerAssignment, TestBulkDueDates, TestBulkTagOperations, TestBulkArchive, TestBulkPriority, TestValidation, TestProgressTracking, TestRollback, TestErrorHandling, TestResultRetrieval, TestAsyncExecution, TestConvenienceMethods, TestResultSummary, TestCustomHandlers, TestLargeScale
- Functions: None

### backend/tests/services/test_business_continuity.py
- Size: 8352 bytes
- Lines: 264
- Classes: TestStoreAndForward, TestConflictResolution, TestRTORPO, TestRestoreRehearsal
- Functions: svc, _utcnow

### backend/tests/services/test_capa_workflow.py
- Size: 37814 bytes
- Lines: 1171
- Classes: TestNCType, TestNCSeverity, TestCAPAType, TestCAPAStatus, TestClosureGateType, TestLinkType, TestCAPAConfig, TestNonConformance, TestCorrectiveAction, TestServiceInitialization, TestNCRegistration, TestCAPACreation, TestRootCauseAnalysis, TestActionManagement, TestEntityLinking, TestClosureGates, TestEffectivenessCheck, TestCAPAClosure, TestStatusUpdates, TestMetrics
- Functions: service, user_id, product_id

### backend/tests/services/test_certification_tracking.py
- Size: 6044 bytes
- Lines: 205
- Classes: None
- Functions: test_registry_requires_write_role, test_registry_self_view_and_privileged_view, test_evidence_masking_for_non_privileged, test_recertification_nudges_60_day_lead_and_idempotent, test_expire_and_renew_emits_events

### backend/tests/services/test_change_control.py
- Size: 26984 bytes
- Lines: 788
- Classes: TestEnums, TestServiceInitialization, TestChangeRequestCreation, TestChangeRequestRetrieval, TestChangeRequestUpdates, TestWorkflow, TestApprovalPolicy, TestChangeApplication, TestRollback, TestPolicies, TestSnapshots, TestAudit, TestReporting, TestConfiguration, TestEdgeCases
- Functions: None

### backend/tests/services/test_chaos_testing.py
- Size: 34259 bytes
- Lines: 942
- Classes: TestScenarioManagement, TestFailureInjection, TestJobRetryTesting, TestGracefulDegradation, TestCircuitBreaker, TestTestRunManagement, TestRecoveryMetrics, TestSummary, TestSingleton, TestClearData
- Functions: service

### backend/tests/services/test_cognitive_obeya.py
- Size: 32714 bytes
- Lines: 948
- Classes: TestEnums, TestDataModels, TestPrescriptiveMetricAnalyzer, TestCrossFunctionalSynergyEngine, TestHeijunkaAdvisor, TestCognitiveObeya, TestFactoryFunctions, TestCognitiveObeyaIntegration
- Functions: metric_analyzer, synergy_engine, heijunka_advisor, obeya

### backend/tests/services/test_common_thread.py
- Size: 4170 bytes
- Lines: 134
- Classes: None
- Functions: None

### backend/tests/services/test_compensation_management.py
- Size: 16799 bytes
- Lines: 555
- Classes: TestRBAC, TestPayBands, TestCompensationRecords, TestChangeWorkflow, TestExport, TestAudit
- Functions: svc

### backend/tests/services/test_conditions_library.py
- Size: 45461 bytes
- Lines: 1197
- Classes: TestDefaultTemplates, TestTemplateCRUD, TestTemplateListing, TestTemplateRendering, TestConditionApplication, TestHardStopsAndWarnings, TestConditionSets, TestBulkOperations, TestValidation, TestExport, TestStatistics, TestModuleFunctions, TestEdgeCases
- Functions: service, entity_id, user_id

### backend/tests/services/test_content_scanning.py
- Size: 21382 bytes
- Lines: 698
- Classes: TestDefaultSignatures, TestSignatureManagement, TestFileTypeManagement, TestPolicyManagement, TestFileScanning, TestTextScanning, TestURLScanning, TestReportManagement, TestQuarantine, TestSummary, TestEdgeCases
- Functions: None

### backend/tests/services/test_context_bus.py
- Size: 4830 bytes
- Lines: 157
- Classes: None
- Functions: None

### backend/tests/services/test_continuous_learning.py
- Size: 20569 bytes
- Lines: 610
- Classes: TestFeedbackCollector, TestIncrementalLearner, TestRetrainingManager, TestContinuousLearningService, TestSingleton, TestIntegration
- Functions: None

### backend/tests/services/test_cost_accounting.py
- Size: 7959 bytes
- Lines: 270
- Classes: None
- Functions: _setup_minimal_coa, test_wip_rollup_from_material_labor_overhead, test_completion_posts_variances_to_gl_and_creates_fg_inventory, test_cogs_and_margin_reporting

### backend/tests/services/test_csv_export.py
- Size: 31561 bytes
- Lines: 1041
- Classes: TestBasicExport, TestColumnConfiguration, TestFiltering, TestSorting, TestPagination, TestFormatOptions, TestValueTransformers, TestExportTemplates, TestConvenienceMethods, TestResultManagement, TestDefaultColumns, TestEdgeCases
- Functions: None

### backend/tests/services/test_csv_import.py
- Size: 48231 bytes
- Lines: 1266
- Classes: TestCSVParsing, TestFieldMappingDetection, TestValidation, TestDuplicateDetection, TestImportExecution, TestImportJobs, TestAuditLogging, TestTemplateGeneration, TestStatistics, TestFieldMappingTypes, TestEdgeCases, TestContactAccountLookup, TestImportTiming, TestFullIntegration
- Functions: service, account_csv, contact_csv, opportunity_csv, account_config, contact_config

### backend/tests/services/test_data_hygiene_nudges.py
- Size: 28965 bytes
- Lines: 909
- Classes: TestFieldRules, TestNudgeGeneration, TestNudgeLifecycle, TestNudgeRetrieval, TestSuppressionRules, TestHygieneScoring, TestHygieneReports, TestBulkOperations, TestStaleData, TestCleanup, TestEdgeCases
- Functions: None

### backend/tests/services/test_data_lineage.py
- Size: 6953 bytes
- Lines: 231
- Classes: None
- Functions: None

### backend/tests/services/test_data_quality.py
- Size: 20817 bytes
- Lines: 614
- Classes: TestValidationRule, TestValidationError, TestValidationResult, TestDataQualityService
- Functions: mock_db_session, service

### backend/tests/services/test_data_retention.py
- Size: 28286 bytes
- Lines: 867
- Classes: TestDefaultPolicies, TestPolicyManagement, TestLegalHolds, TestRetentionStatus, TestArchiveOperations, TestDeleteOperations, TestAnonymization, TestRetentionJobs, TestApproachingExpiry, TestReports, TestEdgeCases
- Functions: None

### backend/tests/services/test_database_backup.py
- Size: 17788 bytes
- Lines: 504
- Classes: TestDatabaseBackupService, TestBackupMetadata, TestRestoreTest, TestBackupSchedule
- Functions: temp_backup_dir, mock_db_session, mock_db_session_factory, service

### backend/tests/services/test_device_management.py
- Size: 4606 bytes
- Lines: 151
- Classes: TestDeviceProfiles, TestDeviceEnrollment, TestRemoteCommands
- Functions: svc

### backend/tests/services/test_digest_export.py
- Size: 54266 bytes
- Lines: 1507
- Classes: TestDigestType, TestDigestFrequency, TestDigestDeliveryChannel, TestDigestStatus, TestWeekDay, TestDigestSchedule, TestDigestRecipient, TestDigestSection, TestTodayDigestContent, TestWeekInReviewContent, TestObeyaDigestContent, TestSectionBuilders, TestDigestExportServiceConfiguration, TestDigestExportServiceRecipients, TestDigestExportServiceSchedule, TestDigestExportServiceContentBuilding, TestDigestExportServiceGeneration, TestDigestExportServiceRetrieval, TestDigestExportServiceJobs, TestDigestExportServiceDelivery
- Functions: None

### backend/tests/services/test_disaster_recovery_drill.py
- Size: 26718 bytes
- Lines: 770
- Classes: TestTargetManagement, TestConfiguration, TestScheduling, TestDrillExecution, TestReporting, TestSingleton, TestClearData
- Functions: service

### backend/tests/services/test_dispatch_traveler.py
- Size: 25676 bytes
- Lines: 763
- Classes: TestRBAC, TestRouteDefinition, TestTraveler, TestOperationExecution, TestCheckpoints, TestDispatching, TestGenealogy, TestAudit
- Functions: svc, ops_roles, operator_roles, reader_roles, norole, route_id

### backend/tests/services/test_document_intelligence.py
- Size: 28388 bytes
- Lines: 870
- Classes: TestBoundingBox, TestExtractedTable, TestProcessedDocument, TestDocumentClassifier, TestKeyValueExtractor, TestEngineeringDrawingProcessor, TestLayoutModel, TestTableStructureModel, TestOCREngine, TestVisionLLMEnricher, TestDocumentIntelligenceService, TestDocumentIntelligenceIntegration, TestDocumentIntelligencePerformance, TestDocumentIntelligenceEdgeCases
- Functions: None

### backend/tests/services/test_document_regional.py
- Size: 23751 bytes
- Lines: 734
- Classes: TestRegionalConfiguration, TestTaxCalculations, TestContributionCalculations, TestLeaveAccrual, TestLogoAssetRegistry, TestLetterheadTemplates, TestInvoiceGeneration, TestPayslipGeneration, TestCOCGeneration, TestElectronicSignature, TestDocumentIntegrity, TestSOSReminders, TestRBAC, TestAuditTrail
- Functions: svc, admin_roles, finance_roles, ops_roles, auditor_roles, viewer_roles

### backend/tests/services/test_edge_ai.py
- Size: 37358 bytes
- Lines: 1038
- Classes: TestEnums, TestDataModels, TestConv1DLayer, TestMaxPool1DLayer, TestDenseLayer, TestEdgeCNN1D, TestPredictiveMaintenanceEngine, TestProtobufLikeEncoder, TestPriorityMessageQueue, TestEdgeToCoreSyncManager, TestFactoryFunctions, TestEdgeAIIntegration
- Functions: sample_sensor_reading, anomaly_sensor_reading, cnn_config, predictive_engine, sync_manager, sample_edge_message, sample_anomaly_detection

### backend/tests/services/test_ehs_safety.py
- Size: 37641 bytes
- Lines: 1018
- Classes: TestEnums, TestDataModels, TestIncidentManagement, TestJSAManagement, TestCertificationManagement, TestSafetyGating, TestSafetyAlerts, TestAuditPackGeneration, TestStatistics, TestFactoryFunction, TestEdgeCases
- Functions: service, sample_incident, sample_near_miss, sample_jsa, sample_certification

### backend/tests/services/test_employee_lifecycle.py
- Size: 5085 bytes
- Lines: 177
- Classes: None
- Functions: now, service, test_employee_profile_pii_masked_for_non_privileged, test_onboarding_checklist_status_transitions, test_offboarding_checklist_contains_exit_interview, test_personnel_file_redacts_for_non_privileged, test_personnel_file_requires_hr_write

### backend/tests/services/test_enhanced_ml_pipeline.py
- Size: 42997 bytes
- Lines: 1328
- Classes: TestFeatureDefinition, TestFeatureVector, TestFeatureGroup, TestModelMetrics, TestModelVersion, TestDriftDetectionResult, TestExperiment, TestABTest, TestFeatureStore, TestModelRegistryService, TestDriftDetector, TestExperimentTracker, TestAutoMLService, TestModelMonitor, TestEnhancedMLPipelineService, TestEnhancedMLPipelineIntegration, TestEnhancedMLPipelineEdgeCases, TestEnhancedMLPipelinePerformance
- Functions: None

### backend/tests/services/test_enrichment.py
- Size: 4167 bytes
- Lines: 117
- Classes: None
- Functions: test_ceo_enrichment, test_knowledge_enrichment

### backend/tests/services/test_erp_integration.py
- Size: 47728 bytes
- Lines: 1307
- Classes: TestFieldTransformer, TestEntityMapping, TestLookupTables, TestUoMConversion, TestTaxCodes, TestDataTransformation, TestSynchronization, TestReconciliationQueue, TestCircuitBreaker, TestWebhooks, TestSyncJobs, TestTransactionalSync, TestConflictDetection, TestHealthDiagnostics, TestFactoryFunction, TestDataModels, TestEnums
- Functions: erp_service, erp_service_with_factory, sample_customer_data, sample_sensei_customer, field_transformer

### backend/tests/services/test_escalation_policy.py
- Size: 43697 bytes
- Lines: 1212
- Classes: TestServiceInitialization, TestPolicyManagement, TestThresholdConfiguration, TestAgingApprovalDetection, TestValueBasedApprovalEscalation, TestHighSeverityRiskDetection, TestOverdueRiskDetection, TestAndonSLABreachDetection, TestEscalationResult, TestEscalationItem, TestHelperMethods, TestEscalationJobRunner, TestMultipleEntities, TestEdgeCases
- Functions: service, reference_time, sample_approval, sample_risk, sample_andon

### backend/tests/services/test_exceptions_aggregator.py
- Size: 30854 bytes
- Lines: 842
- Classes: TestExceptionItem, TestAggregatorInitialization, TestSourceRegistration, TestExceptionManagement, TestFiltering, TestSummary, TestNavigationBadges, TestTrends, TestListeners, TestSingleton, TestCaching, TestSorting
- Functions: aggregator, db, sample_exception, sample_exceptions

### backend/tests/services/test_factory_launchpad.py
- Size: 49641 bytes
- Lines: 1246
- Classes: TestEnums, TestConstants, TestSiteConfig, TestChecklistItem, TestLevelUpChecklist, TestMaturityManager, TestUIVisibilityManager, TestHardwareRolloutTracker, TestFactoryLaunchpad, TestIntegration, TestFactoryFunctions
- Functions: maturity_manager, launchpad, hardware_tracker, registered_site

### backend/tests/services/test_financial_operational_feedback.py
- Size: 5263 bytes
- Lines: 168
- Classes: None
- Functions: _dt, test_reconcile_skips_unknown_cost_center_and_records_issue, test_reconcile_ingests_labor_with_employee_rate_and_updates_work_order_costs, test_variance_alert_triggered_when_actual_cogs_exceeds_threshold

### backend/tests/services/test_fixed_assets.py
- Size: 35374 bytes
- Lines: 1066
- Classes: TestFixedAssetsRBAC, TestCapitalization, TestDepreciation, TestTransfer, TestImpairment, TestDisposal, TestQueries, TestGLIntegration
- Functions: svc, svc_with_gl, accounting_ledger

### backend/tests/services/test_gm_onboarding.py
- Size: 21843 bytes
- Lines: 649
- Classes: TestOnboardingInitialization, TestProgressTracking, TestStepManagement, TestOnboardingCompletion, TestDashboardTour, TestKeyMetrics, TestFirstActions, TestWorkflowChecklist, TestListeners, TestReset, TestSummary, TestSingleton, TestOnboardingStepProperties, TestOnboardingProgressProperties
- Functions: service, user_id, started_onboarding

### backend/tests/services/test_guardrails_performance.py
- Size: 34774 bytes
- Lines: 1035
- Classes: TestEnums, TestResourceMetrics, TestAITask, TestLoadedModel, TestResourceMonitor, TestModelManager, TestPIIRedactor, TestHITLConsistencyMonitor, TestFactoryFunctions, TestEdgeCases, TestIntegration
- Functions: resource_monitor, model_manager, pii_redactor, hitl_monitor, sample_task, sample_model

### backend/tests/services/test_health_checks.py
- Size: 18917 bytes
- Lines: 538
- Classes: TestHealthCheckService, TestResourceMetrics, TestScalingRecommendation, TestDependencyHealth
- Functions: _utcnow, mock_db_session, mock_db_session_factory, mock_redis, mock_s3, service, full_service

### backend/tests/services/test_hr_case_management.py
- Size: 18695 bytes
- Lines: 644
- Classes: TestRBAC, TestCaseLifecycle, TestNotes, TestEvidence, TestActions, TestRetention, TestAudit
- Functions: svc

### backend/tests/services/test_hybrid_search.py
- Size: 37515 bytes
- Lines: 1105
- Classes: TestTokenEstimator, TestRecursiveCharacterSplitter, TestTokenAwareChunker, TestRerankCache, TestONNXCrossEncoder, TestInMemorySemanticSearcher, TestInMemoryKeywordSearcher, TestHybridSearchEngine, TestDynamicContextSizer, TestFactoryFunctions, TestEnums, TestIntegration
- Functions: sample_chunk, sample_document, token_estimator, recursive_splitter, chunker, rerank_cache, reranker, semantic_searcher, keyword_searcher, hybrid_engine, context_sizer

### backend/tests/services/test_hypercare.py
- Size: 6002 bytes
- Lines: 193
- Classes: TestUserFeedback, TestConfigChangeControl, TestEnvironmentSync, TestSeedJobs, TestGoLiveChecklist
- Functions: svc, _utcnow

### backend/tests/services/test_i18n_backend.py
- Size: 24611 bytes
- Lines: 769
- Classes: TestLocaleConfiguration, TestBasicTranslation, TestInterpolation, TestPluralization, TestAddAndUpdateTranslations, TestNamespaces, TestMissingTranslations, TestImportExport, TestNumberFormatting, TestCurrencyFormatting, TestDateFormatting, TestStatistics, TestValidation, TestTranslationKeyProperties, TestEdgeCases
- Functions: None

### backend/tests/services/test_identity_access.py
- Size: 5010 bytes
- Lines: 151
- Classes: TestSSOProvider, TestConditionalAccess
- Functions: svc

### backend/tests/services/test_incident_flow.py
- Size: 37829 bytes
- Lines: 1091
- Classes: TestEnums, TestSeverityConfiguration, TestOnCallSchedule, TestEscalationPolicy, TestIncidentManagement, TestNotifications, TestSLAChecking, TestMetrics, TestSummary, TestEdgeCases, TestIntegration
- Functions: service, sample_incident, on_call_person, sample_schedule

### backend/tests/services/test_industrial_ux.py
- Size: 6075 bytes
- Lines: 182
- Classes: TestThemeConfiguration, TestHIDScannerFeedback, TestVoiceNotes, TestBackgroundSyncResilience
- Functions: svc

### backend/tests/services/test_inline_comments.py
- Size: 42243 bytes
- Lines: 1353
- Classes: TestCommentCreation, TestCommentRetrieval, TestCommentUpdates, TestCommentDeletion, TestCommentResolution, TestPinning, TestThreading, TestReactions, TestNotifications, TestWatchers, TestTaskConversion, TestUserMentions, TestSearch, TestActivityFeed, TestHTMLRendering, TestEdgeCases
- Functions: service, sample_users, sample_team, sample_role, quote_id

### backend/tests/services/test_integration_reconciliation.py
- Size: 26596 bytes
- Lines: 809
- Classes: TestSyncContracts, TestSyncOperations, TestConflictResolution, TestBankImportExport, TestReconciliation, TestRBAC, TestAuditTrail
- Functions: svc, admin_roles, finance_roles, it_roles, auditor_roles, viewer_roles

### backend/tests/services/test_integration_tests.py
- Size: 23060 bytes
- Lines: 728
- Classes: TestEnums, TestDataclasses, TestServiceInitialization, TestDefaultTests, TestTestManagement, TestTestSuites, TestTestExecution, TestExecutionHistory, TestStatisticsAndReporting, TestTestSteps, TestTestProperties, TestMultipleFilters, TestExecutionEnvironment
- Functions: None

### backend/tests/services/test_intelligent_ingestion.py
- Size: 33444 bytes
- Lines: 995
- Classes: TestEnums, TestTableData, TestBOMEntry, TestExtractedBOM, TestDrawingSpec, TestParsingResult, TestOCREngine, TestVisionLLMParser, TestTableExtractor, TestMultiPageStitcher, TestStandardWorkManager, TestUniversalZeroShotParser, TestFactory, TestEdgeCases, TestIntegration, TestConstants
- Functions: sample_document_data, sample_pdf_data, sample_image_data, sample_cad_data, sample_table_data, sample_pages, standard_work_version_v1, standard_work_version_v2

### backend/tests/services/test_jidoka_error_proofing.py
- Size: 2472 bytes
- Lines: 84
- Classes: None
- Functions: None

### backend/tests/services/test_jit_lean_learning.py
- Size: 32271 bytes
- Lines: 884
- Classes: TestEnums, TestDataModels, TestMicroLessonEngine, TestKnowledgeRetrievalEngine, TestStandardWorkEvolutionEngine, TestJITLeanLearning, TestFactoryFunctions, TestJITLeanLearningIntegration
- Functions: lesson_engine, knowledge_engine, evolution_engine, jit_learning

### backend/tests/services/test_job_health.py
- Size: 34580 bytes
- Lines: 1121
- Classes: TestEnums, TestJobDefinition, TestExecution, TestWorker, TestQueue, TestHealthCheck, TestAlerts, TestMetrics, TestSummary, TestIntegration
- Functions: service, sample_job, sample_execution, sample_worker

### backend/tests/services/test_job_idempotency.py
- Size: 47284 bytes
- Lines: 1430
- Classes: TestIdempotencyKey, TestJobLock, TestRetryConfig, TestJobRecord, TestJobResult, TestJobExecutionStats, TestJobIdempotencyService, TestConvenienceFunctions, TestJobIdempotencyIntegration
- Functions: _utcnow

### backend/tests/services/test_knowledge_embeddings.py
- Size: 17156 bytes
- Lines: 470
- Classes: TestEmbeddingService, TestKnowledgeEmbeddingService, TestSemanticSearchService
- Functions: mock_sentence_transformer, embedding_service

### backend/tests/services/test_knowledge_enrichment.py
- Size: 20485 bytes
- Lines: 644
- Classes: TestDefaultSources, TestSourceManagement, TestAcquisition, TestIngestion, TestChunking, TestEmbedding, TestAlignment, TestKnowledgePacks, TestSearch, TestStatistics, TestRBAC, TestAuditTrail
- Functions: svc, admin_roles, curator_roles, reader_roles, viewer_roles

### backend/tests/services/test_knowledge_ingestion.py
- Size: 19755 bytes
- Lines: 533
- Classes: TestLicenseVerifier, TestContentNormalizer, TestSemanticChunker, TestQualityFilter, TestTaxonomyTagger, TestKnowledgePackIngestionService, TestIntegration
- Functions: None

### backend/tests/services/test_kpi_metric_sources.py
- Size: 26983 bytes
- Lines: 877
- Classes: TestDefaultMetrics, TestMetricManagement, TestFiltering, TestFieldSources, TestEventSources, TestValueRecording, TestValueRetrieval, TestTrendCalculation, TestRefresh, TestSourceDocumentation, TestValidation, TestMetricsBySource, TestExportImport, TestDashboardSummary, TestEdgeCases
- Functions: None

### backend/tests/services/test_kpi_metrics.py
- Size: 34622 bytes
- Lines: 1012
- Classes: TestEnums, TestKPIDefinitionManagement, TestDefaultKPIs, TestKPIValues, TestStatusCalculation, TestKPICalculation, TestTrendAnalysis, TestDashboards, TestDefaultDashboards, TestHelperFunctions, TestIntegration
- Functions: service, custom_kpi

### backend/tests/services/test_label_printing.py
- Size: 32858 bytes
- Lines: 923
- Classes: TestEnums, TestDataModels, TestTemplateManagement, TestPrinterManagement, TestBarcodeGeneration, TestPrintQueueManagement, TestScanValidation, TestLabelGeneration, TestStatistics, TestFactoryFunction, TestEdgeCases
- Functions: service, sample_printer, sample_template

### backend/tests/services/test_leave_management.py
- Size: 27947 bytes
- Lines: 911
- Classes: TestRBAC, TestAccrualPolicies, TestHolidayCalendars, TestLeaveBalances, TestLeaveRequests, TestPayrollExport, TestCarryOver, TestAudit
- Functions: svc, svc_with_policy

### backend/tests/services/test_local_first_infrastructure.py
- Size: 35522 bytes
- Lines: 978
- Classes: TestEnums, TestDataclasses, TestMemoryManager, TestCircuitBreaker, TestRegexFallback, TestHeuristicFallback, TestFallbackManager, TestONNXModelSession, TestONNXModelManager, TestONNXOptimizer, TestLocalFirstService, TestSingleton, TestEdgeCases, TestIntegration
- Functions: memory_manager, circuit_breaker, regex_fallback, heuristic_fallback, fallback_manager, model_config, mock_onnx_session, model_session, local_first_service

### backend/tests/services/test_locale_formats.py
- Size: 37692 bytes
- Lines: 979
- Classes: TestEnums, TestCurrencyInfo, TestLocaleConfig, TestNameConstants, TestServiceInitialization, TestUserLocale, TestDateFormatting, TestDateParsing, TestTimeFormatting, TestDatetimeFormatting, TestNumberFormatting, TestNumberParsing, TestCurrencyFormatting, TestCurrencyInfoService, TestRelativeTime, TestDurationFormatting, TestUtilityMethods, TestEdgeCases, TestIntegration
- Functions: service, sample_date, sample_datetime, sample_time

### backend/tests/services/test_lot_serial_traceability.py
- Size: 41395 bytes
- Lines: 1115
- Classes: TestEnums, TestDataModels, TestLotManagement, TestSerialManagement, TestGenealogyManagement, TestWhereUsedIntelligence, TestCertificateBinding, TestRecallManagement, TestStatistics, TestFactoryFunction, TestEdgeCases
- Functions: service, sample_lot, sample_serial

### backend/tests/services/test_lsw_scheduling.py
- Size: 31483 bytes
- Lines: 798
- Classes: TestServiceInitialization, TestTemplateManagement, TestChecklistGeneration, TestChecklistInstanceActions, TestChecklistRetrieval, TestStatusUpdates, TestAnalytics, TestFrequencyScheduling, TestHelperFunctions, TestEdgeCases, TestIntegration
- Functions: service, owner_id, custom_template

### backend/tests/services/test_maintenance_tpm.py
- Size: 35027 bytes
- Lines: 961
- Classes: TestEnums, TestDataModels, TestAssetManagement, TestPMScheduleManagement, TestWorkOrderManagement, TestDowntimeAndOEE, TestMTBFMTTR, TestSparePartsManagement, TestStatistics, TestFactoryFunction, TestEdgeCases
- Functions: service, sample_asset, sample_pm_schedule, sample_work_order, sample_spare_part

### backend/tests/services/test_mentions_assignments.py
- Size: 53258 bytes
- Lines: 1367
- Classes: TestEnums, TestDataModels, TestUtilityFunctions, TestMentionsAssignmentsService, TestUserTeamManagement, TestMentionParsing, TestAssignmentManagement, TestTaskFromComment, TestDueDateManagement, TestReassignment, TestNotifications, TestMentionNotificationProcessing, TestServiceCleanup, TestIntegration
- Functions: None

### backend/tests/services/test_meta_sensei.py
- Size: 52566 bytes
- Lines: 1518
- Classes: SampleClass, TestEnums, TestAutonomousKnowledgeSynthesizer, TestSemanticDeduplicator, TestSiteSpecificLearner, TestDocImplementationSync, TestDevelopmentPlanTracker, TestOnDeviceCodeAuditor, TestAutonomousRefactoringSuggestor, TestBestPracticeExtractor, TestPrivacyPreservingAggregator, TestA3RecommendationEvolver, TestMetaSensei, TestFactoryFunctions, TestDataModels, TestEdgeCases
- Functions: sample_corrections, sample_chunks, sample_quotes, sample_a3s, temp_source_dir, simple_function, dangerous_function, temp_doc_file, temp_plan_file

### backend/tests/services/test_metric_sources.py
- Size: 52641 bytes
- Lines: 1346
- Classes: TestEnums, TestFieldMapping, TestFilterCondition, TestMetricSourceDefinition, TestMetricSourceValidation, TestMetricSourceUsage, TestServiceInitialization, TestSourceRegistration, TestSourceRetrieval, TestSourceUpdate, TestSourceDeletion, TestValidation, TestUsageTracking, TestDocumentation, TestSummary, TestDefaultSources, TestEdgeCases, TestIntegration
- Functions: service, custom_source, duration_source, percentage_source

### backend/tests/services/test_missing_info_workflow.py
- Size: 49919 bytes
- Lines: 1386
- Classes: TestMissingFieldCategory, TestMissingFieldPriority, TestInfoRequestStatus, TestTaskStatus, TestReminderFrequency, TestMissingFieldSpec, TestIdentifiedMissingField, TestRFQData, TestWorkflowConfig, TestServiceInitialization, TestFieldSpecifications, TestRFQAnalysis, TestEmailTemplates, TestEmailGeneration, TestInfoRequests, TestRequestStatusTransitions, TestReminders, TestExpiration, TestTaskManagement, TestFullWorkflow
- Functions: _utcnow, service, sample_rfq_data, complete_rfq_data

### backend/tests/services/test_mrp_lite.py
- Size: 25722 bytes
- Lines: 817
- Classes: TestRBAC, TestBOM, TestInventory, TestDemand, TestMRPRun, TestSuggestionApproval, TestReporting, TestAudit
- Functions: svc, ops_roles, planner_roles, reader_roles, norole

### backend/tests/services/test_muda_nudging_worker.py
- Size: 3203 bytes
- Lines: 114
- Classes: None
- Functions: None

### backend/tests/services/test_multi_agent_rfq.py
- Size: 27480 bytes
- Lines: 834
- Classes: TestRFQSpec, TestTechnicalAgent, TestCommercialAgent, TestRiskAgent, TestAgentOrchestrator, TestDebateProtocol, TestComprehensiveAnalysis, TestMultiAgentRFQAnalyzer, TestFactoryFunction, TestEnums, TestIntegration
- Functions: now, sample_rfq, technical_agent, commercial_agent, risk_agent, orchestrator, analyzer

### backend/tests/services/test_nlp_command_palette.py
- Size: 27933 bytes
- Lines: 792
- Classes: TestFuzzyMatcher, TestActionParser, TestConversationSession, TestConversationManager, TestNLPCommandPalette, TestEntity, TestParsedAction, TestFactoryFunction, TestEnums, TestIntegration
- Functions: _utcnow, fuzzy_matcher, action_parser, conversation_manager, command_palette, sample_session

### backend/tests/services/test_notification_triggers.py
- Size: 43893 bytes
- Lines: 1319
- Classes: TestTriggerType, TestRecipientRole, TestNotificationPriority, TestTriggerCondition, TestGeneratedNotification, TestNotificationTarget, TestNotificationTriggersService, TestTaskEvaluation, TestRFQEvaluation, TestQuoteEvaluation, TestCertificationEvaluation, TestSnoozeAndAcknowledge, TestNotificationTriggersJobRunner, TestEdgeCases, TestNotificationContent, TestUserSnoozeSettings
- Functions: service, now, user1_id, user2_id, users

### backend/tests/services/test_npi_risk_register.py
- Size: 32664 bytes
- Lines: 1067
- Classes: TestRiskCreation, TestRiskRetrieval, TestRiskUpdates, TestMitigationActions, TestRiskReviews, TestTemplates, TestAnalytics, TestEdgeCases, TestCompleteWorkflow
- Functions: service, sample_risk, project_id

### backend/tests/services/test_npi_stage_gates.py
- Size: 35336 bytes
- Lines: 1084
- Classes: TestProjectManagement, TestArtifactManagement, TestStageTransitions, TestGateReviews, TestReadinessAssessment, TestCompleteWorkflow, TestEdgeCases
- Functions: service, sample_project

### backend/tests/services/test_onnx_cross_encoder.py
- Size: 9993 bytes
- Lines: 301
- Classes: TestCrossEncoderConfig, TestCrossEncoderCache, TestTFIDFScorer, TestONNXCrossEncoder, TestGetCrossEncoder
- Functions: None

### backend/tests/services/test_onnx_edge_inference.py
- Size: 8302 bytes
- Lines: 258
- Classes: TestONNXEdgeConfig, TestONNXEdgeInference, TestGetONNXEdgeInference, TestEdgeAIWithONNX
- Functions: None

### backend/tests/services/test_onnx_model_init.py
- Size: 7586 bytes
- Lines: 235
- Classes: TestModelValidationResult, TestModelRegistryStatus, TestONNXModelValidator, TestONNXModelRegistry, TestGetModelRegistry, TestInitializeModels, TestConstants
- Functions: None

### backend/tests/services/test_org_structure.py
- Size: 24510 bytes
- Lines: 785
- Classes: TestRBAC, TestOrgUnits, TestPositions, TestAssignments, TestReportingRelations, TestHeadcountAnalytics, TestAudit
- Functions: svc, hr_roles, viewer_roles, norole, company, department

### backend/tests/services/test_ot_network_safety.py
- Size: 6719 bytes
- Lines: 205
- Classes: TestNetworkZoning, TestEdgeCertificates
- Functions: svc, _utcnow

### backend/tests/services/test_payroll_labor_costing.py
- Size: 7565 bytes
- Lines: 226
- Classes: TestPayrollLaborCosting
- Functions: _dt

### backend/tests/services/test_pdf_generation.py
- Size: 45717 bytes
- Lines: 1265
- Classes: TestPDFDocumentType, TestPDFLanguage, TestPDFBrandTemplate, TestWatermarkType, TestBrandingConfig, TestWatermarkConfig, TestPDFGenerationOptions, TestPDFSection, TestQuotePDFData, TestQualificationPDFData, TestTodaySnapshotPDFData, TestObeyaSnapshotPDFData, TestEightDReportPDFData, TestPDFGenerationService, TestTemplateManagement, TestQuotePDFGeneration, TestQualificationPDFGeneration, TestTodaySnapshotPDFGeneration, TestObeyaSnapshotPDFGeneration, TestWeekInReviewPDFGeneration
- Functions: _utcnow

### backend/tests/services/test_pii_controls.py
- Size: 26129 bytes
- Lines: 866
- Classes: TestDefaultFields, TestFieldDefinitionCRUD, TestDataSubjects, TestConsentManagement, TestDataMasking, TestPIIDetection, TestAccessLogging, TestDeletionRequests, TestReporting, TestSummary, TestEdgeCases
- Functions: None

### backend/tests/services/test_plm_drawing_control.py
- Size: 40766 bytes
- Lines: 1077
- Classes: TestEnums, TestDataModels, TestRevisionNumberGenerator, TestDocumentManagement, TestRevisionManagement, TestHashVerification, TestImpactAnalysis, TestShopFloorDistribution, TestPLMSynchronization, TestRevisionComparison, TestSearch, TestStatistics, TestFactoryFunction, TestWatermarks, TestRevisionLinks, TestEdgeCases
- Functions: service, sample_document, sample_revision

### backend/tests/services/test_predictive_utility_forecasting.py
- Size: 30889 bytes
- Lines: 892
- Classes: TestEnums, TestResourceData, TestTimeSeriesPoint, TestSeasonalComponent, TestTrendComponent, TestForecastPoint, TestResourceForecast, TestTimeSeriesDecomposer, TestDemandForecaster, TestResourceForecaster, TestCapacityPlanner, TestWhatIfSimulator, TestPredictiveUtilityEngine, TestFactoryFunction, TestIntegration
- Functions: sample_resource_data, sample_time_series, sample_demand_data, utility_engine

### backend/tests/services/test_predictive_win_loss.py
- Size: 38019 bytes
- Lines: 1135
- Classes: TestEnums, TestFeature, TestConfidenceInterval, TestCounterfactualScenario, TestPredictionResult, TestFeatureEngineer, TestSHAPExplainer, TestLIMEExplainer, TestConfidenceIntervalCalculator, TestCounterfactualAnalyzer, TestWinLossPredictionModel, TestPredictiveWinLossEngine, TestPredictionOutcomeClassification, TestFactoryFunction, TestIntegration
- Functions: sample_features, historical_rfqs, feature_engineer, prediction_model, prediction_engine

### backend/tests/services/test_privacy_compliance.py
- Size: 3451 bytes
- Lines: 130
- Classes: None
- Functions: test_attendance_self_view_allowed, test_attendance_peer_view_denied, test_performance_masking_for_peers, test_retention_policy_crud_and_cleanup, test_retention_write_requires_role

### backend/tests/services/test_production_scheduling.py
- Size: 7035 bytes
- Lines: 219
- Classes: _MaterialsProvider, _ToolingProvider, _SkillsProvider
- Functions: start_at, test_schedules_without_overlap_same_station, test_schedules_parallel_different_stations, test_respects_earliest_start, test_shift_calendar_and_maintenance_windows, test_horizon_blocks_unschedulable, test_resource_unavailable_blocks_scheduling, test_rush_requires_gm_approval, test_priority_orders_tasks

### backend/tests/services/test_productionization.py
- Size: 20800 bytes
- Lines: 645
- Classes: TestGLAccounts, TestSuppliers, TestCustomers, TestInventory, TestImportMigration, TestOpeningBalances, TestRBAC, TestAuditTrail
- Functions: svc, admin_roles, finance_roles, ops_roles, auditor_roles, viewer_roles

### backend/tests/services/test_qms_quality.py
- Size: 24048 bytes
- Lines: 588
- Classes: TestEnums, TestDocumentControl, TestExternalDocs, TestKPIs, TestSupplierQuality, TestAudits, TestRiskRegistry, TestCalibration, TestControlPlans, TestCustomerFeedback, TestFactory
- Functions: service, published_document, supplier_with_stats, gauge_with_measurements

### backend/tests/services/test_query_optimization.py
- Size: 18317 bytes
- Lines: 507
- Classes: TestQueryMetrics, TestQueryOptimizationService, TestIndexRecommendation, TestQueryAnalysis
- Functions: _utcnow, engine, service, service_with_monitoring

### backend/tests/services/test_quote_approval_time_tracking.py
- Size: 29349 bytes
- Lines: 861
- Classes: TestApprovalCriterion, TestQuoteApprovalContext, TestApprovalSession, TestApprovalAlert, TestQuickApprovalOption, TestDefaultOptions, TestQuoteApprovalServiceSessions, TestQuoteApprovalServiceMonitoring, TestQuoteApprovalServiceQuickOptions, TestQuoteApprovalServiceAnalytics, TestQuoteApprovalServiceConfiguration, TestApproverPerformance, TestSingletonPattern
- Functions: service, sample_quote_id, sample_approver_id, sample_context

### backend/tests/services/test_quote_quality.py
- Size: 47576 bytes
- Lines: 1303
- Classes: TestQuoteQualityServiceBasics, TestLineItemChecks, TestPricingChecks, TestMarginChecks, TestValidityChecks, TestTermsChecks, TestAssumptionChecks, TestSupplierQuoteChecks, TestCTQLinkChecks, TestApprovalChecks, TestCustomFieldChecks, TestScoreCalculation, TestHelperFunctions, TestQualityCheckResult, TestEdgeCases, TestIntegration
- Functions: service, custom_config, valid_quote, minimal_quote

### backend/tests/services/test_rbac_enhanced.py
- Size: 19354 bytes
- Lines: 605
- Classes: TestPermissionMatrix, TestPermissionGrants, TestUIVisibility, TestFieldSecurity, TestSoD, TestAuditTrail, TestPermissionMatrixExport
- Functions: svc, admin_roles, finance_roles, hr_roles, ops_roles, auditor_roles, viewer_roles

### backend/tests/services/test_rbac_security_audit.py
- Size: 31648 bytes
- Lines: 907
- Classes: TestSingleton, TestRoleManagement, TestPermissionManagement, TestUserRoleAssignment, TestAuditLogManagement, TestRoleConfigurationVerification, TestPermissionConfigurationVerification, TestUserAssignmentVerification, TestAuditLogIntegrityVerification, TestAccessPatternAnalysis, TestFindingsManagement, TestComplianceReport, TestClearData, TestDataClassSerialization
- Functions: service, sample_role_id, sample_permission_id, sample_user_id

### backend/tests/services/test_readiness_checklists.py
- Size: 30906 bytes
- Lines: 958
- Classes: TestTemplateManagement, TestSupplierReadinessChecklist, TestPPAPChecklist, TestChecklistRetrieval, TestItemManagement, TestChecklistProgress, TestChecklistApproval, TestSectionProgress, TestEdgeCases, TestCompleteWorkflow
- Functions: service, supplier_checklist, ppap_checklist

### backend/tests/services/test_reasoning_engine.py
- Size: 40627 bytes
- Lines: 1136
- Classes: TestKPIMetric, TestA3Report, TestA3PatternAnalyzer, TestSocraticMentor, TestFiveWhysAssistant, TestSenseiReasoningEngine, TestCreateReasoningEngine, TestWebSocketMessage, TestEnums, TestIntegration
- Functions: sample_kpis_before, sample_kpis_after, sample_countermeasure, sample_a3, pattern_analyzer, socratic_mentor, five_whys_assistant, reasoning_engine

### backend/tests/services/test_recruiting.py
- Size: 20930 bytes
- Lines: 662
- Classes: TestRBAC, TestRequisitions, TestCandidates, TestInterviews, TestOffers, TestAudit
- Functions: svc, svc_with_open_req

### backend/tests/services/test_rfq_completeness.py
- Size: 32910 bytes
- Lines: 917
- Classes: MockRFQ, TestServiceInitialization, TestCompletenessCalculation, TestMissingFields, TestQualificationGate, TestEmailGeneration, TestTaskGeneration, TestFieldDefinitions, TestEdgeCases, TestCompletenessResult, TestCompletenessWorkflow
- Functions: None

### backend/tests/services/test_rfq_time_tracking.py
- Size: 37954 bytes
- Lines: 1103
- Classes: TestTaskTarget, TestPauseRecord, TestTaskSession, TestTimeAlert, TestRFQTimeTrackingServiceSessions, TestRFQTimeTrackingServiceMonitoring, TestRFQTimeTrackingServiceTargets, TestRFQTimeTrackingServiceAnalytics, TestRFQTimeTrackingServiceUtility, TestSingletonPattern, TestTaskPerformanceStats, TestUserEfficiencyMetrics, TestDailyTimeBreakdown
- Functions: service, sample_rfq_id, sample_user_id

### backend/tests/services/test_runbooks.py
- Size: 32832 bytes
- Lines: 961
- Classes: TestEnums, TestTemplates, TestRunbookManagement, TestStepManagement, TestVersionManagement, TestExecutionTracking, TestSummary, TestEdgeCases, TestIntegration
- Functions: service, sample_runbook, runbook_with_steps

### backend/tests/services/test_saved_views.py
- Size: 37200 bytes
- Lines: 1026
- Classes: TestEnums, TestFilterCondition, TestDatePresets, TestSavedView, TestSavedViewsService, TestHelperFunctions, TestSavedViewsIntegration
- Functions: None

### backend/tests/services/test_scheduling_maintenance_sync.py
- Size: 4622 bytes
- Lines: 140
- Classes: None
- Functions: start_at, test_sync_work_order_maintenance_blocks_finite_scheduling, test_sync_pm_due_blocks_capacity

### backend/tests/services/test_search.py
- Size: 29691 bytes
- Lines: 754
- Classes: TestEnums, TestSearchableDocument, TestSearchResult, TestSearchResultSet, TestSearchFilter, TestFullTextSearchService, TestSearch, TestQuickSearch, TestSuggestions, TestIndexHelpers, TestEdgeCases, TestRelevanceScoring
- Functions: service, now, owner_id, populated_service

### backend/tests/services/test_security_logging.py
- Size: 4727 bytes
- Lines: 153
- Classes: TestSecurityEvents, TestThreatDetection
- Functions: svc, _utcnow

### backend/tests/services/test_segment_views.py
- Size: 36112 bytes
- Lines: 1235
- Classes: TestDefaultSegments, TestSegmentCreation, TestSegmentRetrieval, TestSegmentFiltering, TestSegmentUpdate, TestSegmentDeletion, TestSegmentDuplication, TestSegmentSharing, TestPinning, TestDefaultSegment, TestUsageTracking, TestFilterEvaluation, TestCriteriaManagement, TestExportImport, TestSummary, TestEdgeCases
- Functions: None

### backend/tests/services/test_self_improving_rag.py
- Size: 34038 bytes
- Lines: 958
- Classes: TestEnums, TestChunkMetadata, TestChunkUtilityTracker, TestInMemoryVectorStore, TestIncrementalIndexManager, TestThrottleManager, TestReindexScheduler, TestSimpleDocumentProcessor, TestSelfImprovingRAGService, TestFactory, TestIntegration, TestEdgeCases
- Functions: _utcnow, chunk_metadata, utility_tracker, vector_store, throttle_config, rag_service

### backend/tests/services/test_semantic_anomaly_detection.py
- Size: 32256 bytes
- Lines: 953
- Classes: TestEnums, TestProcessEvent, TestSentimentResult, TestAnomaly, TestAlertConfig, TestSentimentAnalyzer, TestSequenceAnalyzer, TestAlertManager, TestAnomalyDetectionEngine, TestFactoryFunction, TestIntegration
- Functions: sample_events, negative_sentiment_event, urgent_event, alert_config, detection_engine

### backend/tests/services/test_sensei_autopilot.py
- Size: 30601 bytes
- Lines: 905
- Classes: TestEnums, TestDatabaseTuner, TestStorageManager, TestSelfHealingEngine, TestBackupManager, TestModelLifecycleManager, TestSenseiAutopilot, TestFactoryFunctions, TestEdgeCases, TestConstants
- Functions: db_tuner, storage_manager, healing_engine, backup_manager, model_manager, autopilot, sample_storage_items

### backend/tests/services/test_sensei_command.py
- Size: 47241 bytes
- Lines: 1456
- Classes: TestEnums, TestExecutiveKPIAggregator, TestFinancialHealthMonitor, TestRiskHeatmapGenerator, TestBrainHealthDashboard, TestLearningProgressionAnalytics, TestMaintenanceAuditLog, TestNL2SQLEngine, TestStrategicBriefingGenerator, TestDeepDatabaseAnalytics, TestGlobalAuditTrail, TestCEOSuperView, TestEmployeeIntelligenceAnalytics, TestSenseiCommand, TestFactoryFunctions, TestDataModels, TestEdgeCases
- Functions: sample_kpis, sample_financial_health, sample_risks, sample_employees

### backend/tests/services/test_sensei_nudges.py
- Size: 30160 bytes
- Lines: 990
- Classes: TestDefaultRules, TestRuleManagement, TestNudgeGeneration, TestThresholdConditions, TestDependencyConditions, TestTimeBasedConditions, TestUserDismissals, TestFeedback, TestPatterns, TestSuggestedValues, TestStatistics, TestBulkOperations, TestCriticalNudges, TestExportImport, TestEdgeCases
- Functions: None

### backend/tests/services/test_setup_wizard.py
- Size: 42388 bytes
- Lines: 1057
- Classes: TestEnums, TestDataModels, TestDefaultConfigurations, TestSetupWizardService, TestSetupWizardIntegration
- Functions: reset_storage, user_id, organization_id, service, started_wizard

### backend/tests/services/test_shift_handover_tier_meetings.py
- Size: 5339 bytes
- Lines: 158
- Classes: None
- Functions: svc, now, test_create_and_list_unacknowledged_notes, test_acknowledge_note_hides_when_filtered, test_payloads_can_surface_on_today_screen, test_generate_agenda_from_red_metrics_and_open_andons, test_escalation_creates_derived_item

### backend/tests/services/test_smart_ingestion.py
- Size: 28497 bytes
- Lines: 908
- Classes: None
- Functions: _utcnow, test_detect_document_type_from_mime, test_detect_document_type_from_extension, test_detect_document_type_unknown, test_calculate_checksum, test_normalize_text, test_parse_date, test_parse_number, test_confidence_to_enum, test_extract_company_from_email, test_extract_name_from_email, test_extract_text_from_text_document, test_extract_text_handles_unicode_errors, test_field_extractor_email, test_field_extractor_phone, test_field_extractor_part_number, test_field_extractor_quantity, test_field_extractor_price, test_field_extractor_date, test_field_extractor_material_spec

### backend/tests/services/test_smart_supplier_matchmaker.py
- Size: 32856 bytes
- Lines: 1052
- Classes: TestEnums, TestCapability, TestPerformanceMetrics, TestSupplier, TestRFQRequirement, TestMatchScore, TestSupplierMatch, TestCapabilityGraph, TestSemanticMatcher, TestCapabilityScorer, TestQualityScorer, TestDeliveryScorer, TestPriceScorer, TestReliabilityScorer, TestCertificationScorer, TestCapacityScorer, TestLocationScorer, TestRankAggregator, TestSmartSupplierMatchmaker, TestFactoryFunction
- Functions: sample_capabilities, sample_supplier, sample_suppliers, sample_requirement, matchmaker

### backend/tests/services/test_socratic_pedagogy_rag.py
- Size: 3511 bytes
- Lines: 106
- Classes: TestSocraticPedagogyRAG
- Functions: None

### backend/tests/services/test_spc_scrap_rework.py
- Size: 26063 bytes
- Lines: 816
- Classes: TestRBAC, TestControlCharts, TestSPCMeasurement, TestScrapRecording, TestReworkRecording, TestCOPQReporting, TestAudit
- Functions: svc, quality_roles, finance_roles, reader_roles, norole

### backend/tests/services/test_staffing_roster.py
- Size: 5206 bytes
- Lines: 196
- Classes: None
- Functions: test_shift_and_roster_requires_write_role, test_absence_approval_flow, test_skill_coverage_risk_single_point_of_failure, test_coverage_risk_critical_when_zero, test_view_permission_enforcement

### backend/tests/services/test_stale_detection.py
- Size: 46156 bytes
- Lines: 1169
- Classes: TestStaleThreshold, TestStaleEntity, TestStaleDetectionResult, TestStaleDetectionServiceOpportunities, TestStaleDetectionServiceRFQs, TestStaleDetectionServiceTasks, TestStaleDetectionServiceThresholds, TestStaleDetectionServiceEdgeCases, TestStaleDetectionJobRunner, TestStaleDetectionIntegration
- Functions: stale_service, reference_time, sample_opportunities, sample_rfqs, sample_tasks

### backend/tests/services/test_standard_work_evolution.py
- Size: 6345 bytes
- Lines: 209
- Classes: None
- Functions: None

### backend/tests/services/test_state_machine.py
- Size: 28098 bytes
- Lines: 817
- Classes: MockEntity, TestStateMachineCore, TestOpportunityStateMachine, TestRFQStateMachine, TestQualificationStateMachine, TestTaskStateMachine, TestStateMachineRegistry, TestGateEnforcer, TestTransitionResult, TestDictionaryEntity
- Functions: None

### backend/tests/services/test_supplier_portal_token.py
- Size: 47393 bytes
- Lines: 1351
- Classes: TestTokenType, TestTokenStatus, TestAccessLevel, TestSubmissionStatus, TestFileType, TestTokenConfig, TestSupplierContact, TestValidationResult, TestServiceInitialization, TestTokenGeneration, TestTokenRetrieval, TestTokenValidation, TestAccessLogging, TestTokenManagement, TestSupplierContacts, TestSubmissions, TestSubmissionReview, TestNotifications, TestAnalytics, TestSingleton
- Functions: _utcnow, service, supplier_id, user_id, rfq_id

### backend/tests/services/test_supply_chain_simulation.py
- Size: 28291 bytes
- Lines: 847
- Classes: TestEnums, TestDisruptionScenario, TestSupplyChainNode, TestRFQSimulationInput, TestSimulationResult, TestImpactAnalysis, TestSimulationReport, TestDisruptionLibrary, TestMonteCarloSimulator, TestImpactAnalyzer, TestMitigationAdvisor, TestSupplyChainSimulator, TestFactoryFunction, TestIntegration
- Functions: sample_rfq, sample_supply_chain, logistics_delay_scenario, simulator

### backend/tests/services/test_support_inbox.py
- Size: 27029 bytes
- Lines: 829
- Classes: TestEnums, TestServiceInitialization, TestTicketCreation, TestTicketRetrieval, TestTicketUpdates, TestTicketComments, TestTicketStatus, TestRouting, TestRoutingRules, TestFeedback, TestA3Lite, TestStatistics, TestSLAManagement, TestSearch, TestEdgeCases
- Functions: None

### backend/tests/services/test_talent_performance.py
- Size: 7265 bytes
- Lines: 217
- Classes: TestTalentPerformance
- Functions: _dt

### backend/tests/services/test_template_cloning.py
- Size: 32088 bytes
- Lines: 972
- Classes: TestTemplateManagement, TestEntityCloning, TestDeepCloning, TestCreateFromTemplate, TestQuoteVersioning, TestCloneHistory, TestCloneOptions, TestFieldMappings, TestSystemTemplates, TestEdgeCases
- Functions: None

### backend/tests/services/test_today_screen.py
- Size: 92481 bytes
- Lines: 2622
- Classes: TestPriorityManagement, TestRiskManagement, TestCommitmentManagement, TestAbnormalityManagement, TestMicroDrill, TestLSWChecklistSummary, TestQuickMetrics, TestTodayScreenData, TestSingletonPattern, TestEdgeCases, TestWorkOrdersAtRisk, TestCriticalAndons, TestStationEfficiency, TestCellOEE, TestKanbanAlerts, TestExpiringCertifications, TestWIPViolations, TestCAPAVerifications, TestScheduledTrainings, TestShopFloorSummary
- Functions: service, sample_user_id, sample_user_name

### backend/tests/services/test_tps_knowledge_sources.py
- Size: 25884 bytes
- Lines: 652
- Classes: TestSourceDataIntegrity, TestTopicCoverage, TestCategoryDistribution, TestLicenseDistribution, TestQualityMetrics, TestUtilityFunctions, TestImportantSources, TestSearchAndDiscovery, TestKnowledgeSourceModel, TestKnowledgeBaseCompleteness
- Functions: None

### backend/tests/services/test_tps_teacher.py
- Size: 35370 bytes
- Lines: 993
- Classes: TestEnums, TestDataModels, TestPDCACoachingEngine, TestImprovementKataAssistant, TestMudaDetectionEngine, TestJidokaMentor, TestTPSTeacher, TestFactoryFunctions, TestTPSIntegration
- Functions: pdca_engine, kata_assistant, muda_detector, jidoka_mentor, tps_teacher, sample_process_data

### backend/tests/services/test_training_matrix.py
- Size: 33297 bytes
- Lines: 1018
- Classes: TestServiceInitialization, TestMatrixGeneration, TestGapAnalysis, TestExpirationAlerts, TestUserSkillSummary, TestStationReadiness, TestEdgeCases, TestDataClasses
- Functions: service, reference_date, sample_users, sample_skills, sample_stations, sample_skill_requirements, sample_user_skills

### backend/tests/services/test_ui_backend_integration.py
- Size: 32291 bytes
- Lines: 890
- Classes: TestEnums, TestDataModels, TestErrorMappingService, TestValidationSchemaExportService, TestActionAuditService, TestConnectionHealthService, TestUIBackendIntegration, TestFactoryFunctions, TestUIBackendIntegrationScenarios
- Functions: error_mapping_service, schema_export_service, action_audit_service, connection_health_service, integration

### backend/tests/services/test_virtual_assistant.py
- Size: 32447 bytes
- Lines: 965
- Classes: TestCriticalPathCalculator, TestSLAWatchdog, TestCalendarEntityExtractor, TestBriefingNoteGenerator, TestMeetingPreparationAI, TestSenseiVirtualAssistant, TestDataModels, TestEnums, TestFactoryFunction, TestIntegration
- Functions: now, sample_deadline, sample_event, sla_watchdog, entity_extractor, meeting_prep, virtual_assistant

### backend/tests/services/test_virtual_routing.py
- Size: 36206 bytes
- Lines: 1078
- Classes: TestRoutingCRUD, TestOperationManagement, TestTimeCalculations, TestCostCalculations, TestTemplateManagement, TestRoutingComparison, TestQuickBuilders, TestWorkCenterRates, TestLearningCurve, TestEdgeCases, TestFullIntegration
- Functions: service, sample_routing

### backend/tests/services/test_visual_quality_inspection.py
- Size: 29408 bytes
- Lines: 898
- Classes: TestBoundingBox, TestSegmentationMask, TestDetectedDefect, TestAnomalyMap, TestInspectionResult, TestInspectionBatch, TestPatchCoreDetector, TestYOLODefectDetector, TestQualityScoringEngine, TestContinuousLearningManager, TestVisualQualityInspectionService, TestVisualQualityInspectionIntegration, TestVisualQualityInspectionEdgeCases, TestVisualQualityInspectionPerformance
- Functions: _utcnow, run_async

### backend/tests/services/test_whatif_simulation.py
- Size: 41465 bytes
- Lines: 1248
- Classes: TestScenarioManagement, TestSimulationExecution, TestMultipleAdjustments, TestComparisonAndInsights, TestScenarioComparison, TestQuickSimulationHelpers, TestSensitivityAnalysis, TestBreakEvenAnalysis, TestAdjustmentTypes, TestLineItemChangesTracking, TestEdgeCases, TestFullIntegration
- Functions: service, sample_line_item, sample_line_item_2, sample_quote

### backend/tests/services/test_wms_integration.py
- Size: 36768 bytes
- Lines: 1030
- Classes: TestEnums, TestDataModels, TestZoneManagement, TestLocationManagement, TestInventoryManagement, TestTransactions, TestPicking, TestPutaway, TestCycleCounting, TestGoodsReceipt, TestShipping, TestERPSync, TestStatistics, TestFactoryFunction
- Functions: service, sample_zone, sample_location, sample_inventory

### backend/tests/services/test_world_class_document_ai.py
- Size: 26152 bytes
- Lines: 749
- Classes: TestEnums, TestBoundingBox, TestDocumentElement, TestTableExtraction, TestGDTExtraction, TestTitleBlock, TestDocumentStructure, TestLayoutAnalyzer, TestTableStructureRecognizer, TestVisionLLMEnricher, TestEngineeringDrawingProcessor, TestDocumentClassifier, TestKeyValueExtractor, TestWorldClassDocumentAI, TestIntegrationScenarios, TestErrorHandling, TestGDTRecognition, TestRAGChunkGeneration
- Functions: run_async

### backend/tests/services/test_xai_service.py
- Size: 38392 bytes
- Lines: 1068
- Classes: TestEnums, TestDataModels, TestEvidenceRetriever, TestFeatureAnalyzer, TestCounterfactualGenerator, TestExplanationGenerator, TestAIReasoningAuditTrail, TestXAIService, TestFactoryFunctions, TestXAIIntegration
- Functions: sample_decision, sample_documents, xai_service, audit_trail, explanation_generator, evidence_retriever

### docker-compose.yml
- Size: 6146 bytes
- Lines: 203
- Top-level keys (heuristic): version, services, volumes, networks

### docs/README.md
- Size: 8524 bytes
- Lines: 242
- Headings: # Starz Morocco Manufacturing Management System - Documentation | ## 📚 Documentation Structure | ### For Developers | ### For DevOps/Administrators | ### For End Users | ## 🚀 Quick Links | ### Most Common Tasks | ## 📖 Documentation Categories | ### 1. Architecture | ### 2. Development | ### 3. API | ### 4. Deployment
- First paragraph: Complete documentation for developers, administrators, and end users.

### docs/Resources/Admin/Admin_Starter_Guide.md
- Size: 68585 bytes
- Lines: 1115
- Headings: # Admin Starter Guide | ## Sensei OS - System Administration Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as System Admin | ### Admin Capabilities | ### Admin vs IT Admin | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Admin Console Access
- First paragraph: ---

### docs/Resources/Auditor/Auditor_Starter_Guide.md
- Size: 73035 bytes
- Lines: 1167
- Headings: # Auditor Starter Guide | ## Sensei OS - Auditor Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as Auditor | ### Auditor Capabilities | ### Auditor Independence | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Auditor Home Screen
- First paragraph: ---

### docs/Resources/CEO/CEO_Starter_Guide.md
- Size: 25402 bytes
- Lines: 733
- Headings: # CEO Starter Guide | ## Sensei OS - Chief Executive Officer Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in Sensei OS | ### CEO Capabilities Matrix | ### What Makes CEO Access Unique | ## 2. First Login & Account Setup | ### Initial Login Process | ### MFA Configuration Options | ### Profile Setup Checklist
- First paragraph: ---

### docs/Resources/Executive/Executive_Starter_Guide.md
- Size: 58288 bytes
- Lines: 982
- Headings: # Executive Starter Guide | ## Sensei OS - Executive Leadership Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as an Executive | ### Executive Capabilities | ### Executive Information Flow | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Executive Home Screen
- First paragraph: ---

### docs/Resources/Finance/Finance_Starter_Guide.md
- Size: 60125 bytes
- Lines: 1096
- Headings: # Finance / Accountant Starter Guide | ## Sensei OS - Finance & Accounting Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in Finance | ### Finance Capabilities by Role | ### Finance Module Overview | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Finance Home Screen
- First paragraph: ---

### docs/Resources/General_Manager/GM_Starter_Guide.md
- Size: 40181 bytes
- Lines: 956
- Headings: # General Manager (GM) Starter Guide | ## Sensei OS - General Manager Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as General Manager | ### GM Capabilities Matrix | ### GM vs Other Roles | ## 2. Day 1 Onboarding | ### Your Guided Onboarding Journey | ### Day 1 Checklist | #### Hour 1: Account Setup
- First paragraph: ---

### docs/Resources/HR/HR_Starter_Guide.md
- Size: 60481 bytes
- Lines: 1177
- Headings: # HR Manager Starter Guide | ## Sensei OS - Human Resources Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in HR | ### HR Capabilities | ### What Makes HR Access Unique | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your HR Home Screen
- First paragraph: ---

### docs/Resources/IT/IT_Starter_Guide.md
- Size: 60909 bytes
- Lines: 1148
- Headings: # IT Administrator Starter Guide | ## Sensei OS - IT Administration Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in IT Administration | ### IT Admin Capabilities | ### System Architecture Overview | ## 2. Getting Started | ### First Login as IT Admin | ### Initial Setup Tasks | ### Admin Access Point
- First paragraph: ---

### docs/Resources/Maintenance/Maintenance_Starter_Guide.md
- Size: 46275 bytes
- Lines: 988
- Headings: # Maintenance Technician Starter Guide | ## Sensei OS - Maintenance Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in Maintenance | ### Maintenance Capabilities | ### Maintenance Philosophy | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Maintenance Home Screen
- First paragraph: ---

### docs/Resources/Operator/Operator_Starter_Guide.md
- Size: 36702 bytes
- Lines: 977
- Headings: # Operator Starter Guide | ## Sensei OS - Production Operator Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as Operator | ### What You Can Do in Sensei | ### What Your Screen Looks Like | ## 2. Getting Started | ### Your First Login | ### Setting Up Your Profile | ### Logging Into Your Workstation
- First paragraph: ---

### docs/Resources/Quality/Quality_Starter_Guide.md
- Size: 53343 bytes
- Lines: 1097
- Headings: # Quality Manager / Inspector Starter Guide | ## Sensei OS - Quality Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in Quality | ### Quality Capabilities by Role | ### Quality Workflow Overview | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Quality Home Screen
- First paragraph: ---

### docs/Resources/Sales/Sales_Starter_Guide.md
- Size: 53004 bytes
- Lines: 958
- Headings: # Sales Starter Guide | ## Sensei OS - Sales Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role in Sales | ### Sales Capabilities | ### Sales Success in Sensei OS | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Sales Home Screen
- First paragraph: ---

### docs/Resources/Supervisor/Supervisor_Starter_Guide.md
- Size: 36923 bytes
- Lines: 922
- Headings: # Operations Manager / Supervisor Starter Guide | ## Sensei OS - Operations Supervisor Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as Supervisor | ### Supervisor Capabilities | ### What Makes Supervisor Access Unique | ## 2. Getting Started | ### First Login | ### Initial Profile Setup | ### Understanding Your Home Screen
- First paragraph: ---

### docs/Resources/Team_Lead/Team_Lead_Starter_Guide.md
- Size: 56377 bytes
- Lines: 1057
- Headings: # Team Lead Starter Guide | ## Sensei OS - Team Lead Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as Team Lead | ### Team Lead Capabilities | ### Leadership Philosophy | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Team Lead Dashboard
- First paragraph: ---

### docs/Resources/Warehouse/Warehouse_Starter_Guide.md
- Size: 56586 bytes
- Lines: 1006
- Headings: # Warehouse Manager Starter Guide | ## Sensei OS - Warehouse & Inventory Complete Reference | ## Table of Contents | ## Project Management (Taiga-like) | ## 1. Welcome & Role Overview | ### Your Role as Warehouse Manager | ### Warehouse Capabilities | ### Warehouse Module Overview | ## 2. Getting Started | ### First Login | ### Initial Setup Tasks | ### Your Warehouse Home Screen
- First paragraph: ---

### docs/TEACHING_DOCUMENT.md
- Size: 24225 bytes
- Lines: 665
- Headings: # Sensei OS: Complete System Teaching Document | ## Table of Contents | ## 1. System Overview | ### 1.1 What is Sensei OS? | ### 1.2 Core Principles | ### 1.3 Key Capabilities | ## 2. Architecture & Technology Stack | ### 2.1 Backend Architecture | ### 2.2 Technology Stack | ### 2.3 Service Pattern | # Business logic here | ## 3. Role-Based Access Control (RBAC)
- First paragraph: > **A Comprehensive Guide to the Factory Management Operating System**

### docs/api/README.md
- Size: 4835 bytes
- Lines: 186
- Headings: # API Documentation Index | ## Base URL | ## Authentication | ## API Endpoints | ### Core Resources | #### Accounts & Contacts | #### Opportunities & Sales | #### Products & Manufacturing | #### Quality & Compliance | #### Project Management | #### Training & Learning | #### Operations
- First paragraph: Complete API reference for Sensei Manufacturing Management System.

### docs/architecture/1.1-technology-stack.md
- Size: 5640 bytes
- Lines: 189
- Headings: # Technology Stack Selection & Setup | ## Overview | ## Technology Stack | ### Frontend | ### Backend | ### Database & Storage | ### DevOps & Infrastructure | ## Project Structure | ## Setup Instructions | ### Prerequisites | ### Quick Start | # Edit .env with your settings
- First paragraph: This document describes the technology choices and setup for Sensei OS.

### docs/architecture/1.2-database-schema.md
- Size: 10971 bytes
- Lines: 291
- Headings: # 1.2 Database Schema Design | ## Overview | ## Database Configuration | ## Table Summary | ## Base Model Architecture | ### Common Mixins | ## Entity Relationship Diagram (Simplified) | ## Core Domain Models | ### Users & Authentication | ### Accounts & Contacts | ### CRM Pipeline | ### Quality Management
- First paragraph: Sensei OS uses PostgreSQL 16 with SQLAlchemy 2.0 ORM and Alembic for migrations. The schema is designed around lean manufacturing principles, supporting CRM, quality management, shop floor control, an

### docs/architecture/README.md
- Size: 13760 bytes
- Text: no (binary or unsupported)

### docs/architecture/SYSTEM_DESCRIPTION.md
- Size: 2989 bytes
- Lines: 53
- Headings: # Sensei OS - System Description | ## Overview | ## Core Modules | ### 1. Sales & Commercial | ### 2. Engineering & NPI (New Product Introduction) | ### 3. Production & Shop Floor (MES) | ### 4. Quality Management (QMS) | ### 5. Supply Chain & Logistics | ### 6. Executive & Intelligence | ## Key Architectural Principles | ### Data Lineage (The "Common Thread") | ### Local-First AI
- First paragraph: Sensei OS is a comprehensive Manufacturing Operating System designed to integrate all aspects of a modern factory, from sales and engineering to production and quality. It leverages advanced AI/ML to 

### docs/deployment/DEPLOYMENT.md
- Size: 11536 bytes
- Lines: 537
- Headings: # Kubernetes Deployment Guide | ## Table of Contents | ## Prerequisites | ### Required Tools | ### Cluster Requirements | ### Optional Components | ## Cluster Setup | ### 1. Install cert-manager | # Verify installation | ### 2. Install NGINX Ingress Controller | # Add Helm repository | # Install ingress controller
- First paragraph: This guide covers deploying the Sensei Manufacturing Management System to a Kubernetes cluster using Helm.

### docs/deployment/HETZNER-DEPLOYMENT.md
- Size: 18715 bytes
- Lines: 757
- Headings: # Hetzner Cloud Deployment Guide | ## Table of Contents | ## Why Hetzner Cloud? | ### Recommended Configuration | ## Prerequisites | ### Required Tools | # Install Hetzner CLI | # or | # Install kubectl | # Install Helm | ### Hetzner Account Setup | # Set API token
- First paragraph: Complete guide for deploying Sensei Manufacturing Management System on Hetzner Cloud infrastructure.

### docs/deployment/QUICKSTART.md
- Size: 9102 bytes
- Lines: 474
- Headings: # Quick Start Guide - Local Development | ## Prerequisites | ## Installation | ### 1. Install Required Tools | # Minikube | # kubectl | # Helm | ### 2. Start Minikube | # Start with sufficient resources | # Enable required addons | # Verify cluster | ### 3. Build Container Images
- First paragraph: Deploy Sensei locally using Minikube for development and testing.

### docs/deployment/helm-chart-readme.md
- Size: 6453 bytes
- Lines: 260
- Headings: # Sensei - Manufacturing Management System | ## Prerequisites | ## Installing the Chart | ### Add Bitnami repository | ### Install cert-manager (if not already installed) | ### Install NGINX Ingress Controller (if not already installed) | ### Install Sensei | # Install with default values | # Install with custom values | # Install to specific namespace | ## Configuration | ## Upgrading
- First paragraph: Helm chart for deploying Sensei on Kubernetes with PostgreSQL, Redis, and MinIO.

### docs/deployment/helm-dependencies.md
- Size: 1212 bytes
- Lines: 68
- Headings: # Helm Chart Dependencies | ## Downloading Dependencies | ## Alternative: Update Dependencies | ## Verifying Dependencies | # Should show: | # postgresql-15.5.0.tgz | # redis-19.0.0.tgz | ## Without Dependencies | # In your values.yaml or via --set | # Configure external connections
- First paragraph: This Helm chart depends on Bitnami charts for PostgreSQL and Redis. These dependencies must be downloaded before installation.

### docs/deployment/kubernetes-completion-summary.md
- Size: 15988 bytes
- Lines: 470
- Headings: # Item 7: Kubernetes/Helm Deployment - Completion Summary | ## Overview | ## What Was Built | ### 1. Helm Chart Structure (`/k8s/helm/sensei/`) | #### Chart Configuration (3 files, 528 lines) | ### 2. Kubernetes Manifests (`/k8s/helm/sensei/templates/`) - 14 files, 523 lines | #### Workload Resources (3 files, 183 lines) | #### Networking Resources (2 files, 58 lines) | #### Configuration Resources (2 files, 34 lines) | #### Auto-scaling & High Availability (3 files, 113 lines) | #### Storage & Identity (2 files, 29 lines) | ### 3. Documentation (5 files, 1,349 lines)
- First paragraph: Successfully implemented production-grade Kubernetes deployment using Helm charts, replacing the originally planned Docker Compose approach with enterprise-ready container orchestration.

### docs/development/IMPLEMENTATION_ITEMS_1-5.md
- Size: 10730 bytes
- Lines: 349
- Headings: # Implementation Summary - Development Plan Items 1-5 | ## ✅ Item 1: E2E GM Day-1 Flow Test (COMPLETE) | ## ✅ Item 2: Mobile Responsiveness Verification (COMPLETE) | ## ✅ Item 3: Load Testing Implementation (COMPLETE) | ## ✅ Item 4: Qualification Screen UI Refinement (COMPLETE) | ## ✅ Item 5: Quote Builder UI Refinement (COMPLETE) | ### 1. **Sectioned Layout** | ### 2. **Assumptions Always Visible** (Key Requirement) | ### 3. **Internal Costing Collapsible** (Key Requirement) | ### 4. **Pre-Release Checks Summary** (Key Requirement) | ### 5. **Detailed Line Item Costing** | ### 6. **Enhanced Quote Summary**
- First paragraph: **File**: `frontend/e2e/gm-day1-full-flow.spec.ts` (262 lines)

### docs/development/getting-started.md
- Size: 14678 bytes
- Lines: 652
- Headings: # Development Guide | ## Table of Contents | ## Getting Started | ### Prerequisites | ### Setup Local Environment | #### Backend Setup | # Clone repository | # Create virtual environment | # Install dependencies | # Configure environment | # Edit .env with your local settings | # Run database migrations
- First paragraph: Complete guide for developers working on the Sensei Manufacturing Management System.

### docs/guides/admin-guide.md
- Size: 1559 bytes
- Lines: 41
- Headings: # Administrator Guide | ## System Configuration | ### Environment Variables | ### Admin Dashboard | ## User Management | ### Creating Users | ### RBAC Configuration | ## Security Management | ### Configuring SSO | ### 2FA Enforcement | ## Troubleshooting
- First paragraph: This guide provides information for system administrators to configure and manage Sensei OS.

### docs/guides/configuration-reference.md
- Size: 14492 bytes
- Lines: 668
- Headings: # Configuration Reference | ## 📋 Table of Contents | ## 🔧 Backend Configuration | ### Configuration File Location | ### Core Settings | # Application | # Server | # API | ### Configuration Class | # Application | # Server | # Database
- First paragraph: Complete reference for configuring Starz Morocco Manufacturing Management System.

### docs/guides/project-management.md
- Size: 2921 bytes
- Lines: 74
- Headings: # Project Management (Taiga-like) | ## Permissions & Privacy | ## Where to find it | ## Role quickstarts | ### CEO / Executive | ### General Manager (GM) | ### Supervisor / Team Lead | ### Operator | ### Quality / Engineering | ### Maintenance | ### Sales / Finance / HR / Auditor / Warehouse / IT / Admin
- First paragraph: Sensei OS includes a Taiga-like project module for planning and execution. It’s designed around a few core entities:

### docs/guides/troubleshooting.md
- Size: 15163 bytes
- Lines: 707
- Headings: # Troubleshooting Guide | ## 📋 Table of Contents | ## 🔧 Backend Issues | ### Application Won't Start | # Error: "SECRET_KEY must be set" | # Solution: Create .env file with required variables | # Error: "connection refused" or "could not connect to server" | # Solution: Verify PostgreSQL is running | # Start PostgreSQL if not running | # Check DATABASE_URL format | # postgresql+asyncpg://user:password@localhost:5432/database | # Error: "Address already in use"
- First paragraph: Common issues and solutions for Starz Morocco Manufacturing Management System.

### docs/guides/user-guide.md
- Size: 15184 bytes
- Lines: 663
- Headings: # User Guide | ## 📋 Table of Contents | ## 🚀 Getting Started | ### Logging In | ### Dashboard Overview | ### Navigation | ## 📊 Managing Opportunities | ### Creating an Opportunity | ### Pipeline Stages | ### Opportunity Details | ### Filtering & Sorting | ## 📝 RFQ Process
- First paragraph: Complete guide to using Starz Morocco Manufacturing Management System.

### docs/maintenance/DATABASE.md
- Size: 2126 bytes
- Lines: 61
- Headings: # Database Maintenance Guide | ## Overview | ## Table Partitioning | ### Implementation | ### Benefits | ### Managing Partitions | ## Backup and Recovery | ### Automated Backups | ### Manual Backup | ### Restoration Procedure | ## Performance Monitoring | ### Slow Query Log
- First paragraph: This document describes maintenance procedures for the Sensei OS PostgreSQL database.

### docs/maintenance/ML_SYSTEMS.md
- Size: 2281 bytes
- Lines: 48
- Headings: # Machine Learning Systems Maintenance | ## ML Architecture Overview | ## ML Pipeline | ## Asynchronous Offloading | # In the API endpoint | ## Model Retraining | ## Monitoring Model Health | ## Troubleshooting
- First paragraph: This document describes the maintenance and operations of the AI/ML components in Sensei OS.

### docs/maintenance/SECURITY.md
- Size: 2120 bytes
- Lines: 47
- Headings: # Security Maintenance and Operations | ## Secret Management | ### ExternalSecrets Operator | ### Local Development | ### Rotating Secrets | ## Authentication & Authorization | ### RBAC (Role-Based Access Control) | ### Single Sign-On (SSO) | ### Two-Factor Authentication (2FA) | ## Auditing | ### Audit Logs | ## Vulnerability Scanning
- First paragraph: This document describes the security architecture and maintenance procedures for Sensei OS.

### docs/testing/README.md
- Size: 13871 bytes
- Lines: 593
- Headings: # Testing Guide Index | ## 📋 Testing Overview | ### Test Types | ### Test Coverage | ## 🧪 Backend Testing | ### Running Tests | # Run all tests | # Run specific test file | # Run specific test | # Run with coverage | # Run in parallel (faster) | ### Test Structure
- First paragraph: Comprehensive testing documentation for Starz Morocco Manufacturing Management System.

### docs/testing/e2e-testing.md
- Size: 6232 bytes
- Lines: 180
- Headings: # E2E Tests - GM Day-1 Flow | ## Overview | ## Test Coverage | ### 1. GM Day-1 Setup Wizard (5 tests) | ### 2. Today Screen - Daily Dashboard (7 tests) | ### 3. Approvals Workflow (4 tests) | ### 4. Export Snapshot Functionality (4 tests) | ### 5. Complete Integration Flow (1 test) | ### 6. Mobile Responsiveness (2 tests) | ## Test Structure | ## Test Strategy | ### Graceful Degradation
- First paragraph: Comprehensive end-to-end tests for the General Manager Day-1 onboarding and daily workflow using Playwright.

### frontend/.gitignore
- Size: 609 bytes
- Lines: 60
- Snippet: # Dependencies

### frontend/Dockerfile
- Size: 1088 bytes
- Lines: 47
- Snippet: FROM node:20-alpine AS deps

### frontend/capacitor.config.json
- Size: 1230 bytes
- Lines: 55
- Top-level keys: appId, appName, webDir, server, plugins, android, ios

### frontend/e2e/ceo-exec-path.spec.ts
- Size: 4947 bytes
- Lines: 117
- Exports: None

### frontend/e2e/finance-accountant.spec.ts
- Size: 1662 bytes
- Lines: 46
- Exports: None

### frontend/e2e/gm-admin-path.spec.ts
- Size: 5751 bytes
- Lines: 138
- Exports: None

### frontend/e2e/gm-day1-flow.spec.ts
- Size: 25023 bytes
- Lines: 671
- Exports: None

### frontend/e2e/gm-day1-full-flow.spec.ts
- Size: 3067 bytes
- Lines: 98
- Exports: None

### frontend/e2e/hr-auditor.spec.ts
- Size: 1441 bytes
- Lines: 41
- Exports: None

### frontend/e2e/it-security.spec.ts
- Size: 1760 bytes
- Lines: 46
- Exports: None

### frontend/e2e/lean-ci.spec.ts
- Size: 1525 bytes
- Lines: 44
- Exports: None

### frontend/e2e/login.spec.ts
- Size: 3003 bytes
- Lines: 85
- Exports: None

### frontend/e2e/logistics-shipping.spec.ts
- Size: 1502 bytes
- Lines: 44
- Exports: None

### frontend/e2e/maintenance-planner.spec.ts
- Size: 1516 bytes
- Lines: 44
- Exports: None

### frontend/e2e/maintenance-tech.spec.ts
- Size: 1472 bytes
- Lines: 41
- Exports: None

### frontend/e2e/mobile-responsiveness.spec.ts
- Size: 7584 bytes
- Lines: 221
- Exports: None

### frontend/e2e/navigation.spec.ts
- Size: 3841 bytes
- Lines: 116
- Exports: None

### frontend/e2e/operator-team-lead.spec.ts
- Size: 2373 bytes
- Lines: 59
- Exports: None

### frontend/e2e/performance.spec.ts
- Size: 15668 bytes
- Lines: 468
- Exports: None

### frontend/e2e/project-management.spec.ts
- Size: 4555 bytes
- Lines: 108
- Exports: None

### frontend/e2e/purchasing-procurement.spec.ts
- Size: 1512 bytes
- Lines: 44
- Exports: None

### frontend/e2e/quality-engineering.spec.ts
- Size: 1693 bytes
- Lines: 46
- Exports: None

### frontend/e2e/role-access-audit.spec.ts
- Size: 16732 bytes
- Lines: 466
- Exports: None

### frontend/e2e/role-audit.spec.ts
- Size: 2746 bytes
- Lines: 113
- Exports: None

### frontend/e2e/role-based-access.spec.ts
- Size: 2221 bytes
- Lines: 84
- Exports: None

### frontend/e2e/role-screenshot-analysis.spec.ts
- Size: 3587 bytes
- Lines: 120
- Exports: None

### frontend/e2e/role-screenshot-audit.spec.ts
- Size: 28703 bytes
- Lines: 808
- Exports: None

### frontend/e2e/sales-estimator.spec.ts
- Size: 2746 bytes
- Lines: 72
- Exports: None

### frontend/e2e/supply-chain.spec.ts
- Size: 1599 bytes
- Lines: 45
- Exports: None

### frontend/jest.config.js
- Size: 1090 bytes
- Lines: 39
- Exports: None

### frontend/jest.setup.ts
- Size: 3486 bytes
- Lines: 125
- Exports: None

### frontend/next-env.d.ts
- Size: 201 bytes
- Lines: 6
- Exports: None

### frontend/next.config.js
- Size: 1310 bytes
- Lines: 68
- Exports: None

### frontend/package-lock.json
- Size: 541545 bytes
- Lines: 15066
- Top-level keys: name, version, lockfileVersion, requires, packages

### frontend/package.json
- Size: 3777 bytes
- Lines: 108
- Top-level keys: name, version, private, description, scripts, dependencies, devDependencies, engines

### frontend/playwright.config.ts
- Size: 1864 bytes
- Lines: 67
- Exports: None

### frontend/postcss.config.js
- Size: 83 bytes
- Lines: 7
- Exports: None

### frontend/public/manifest.json
- Size: 1849 bytes
- Lines: 79
- Top-level keys: name, short_name, description, start_url, display, background_color, theme_color, orientation, scope, lang, dir, categories, icons, shortcuts, related_applications, prefer_related_applications, handle_links, launch_handler

### frontend/public/sw.js
- Size: 11607 bytes
- Lines: 431
- Exports: None

### frontend/public/sw.ts
- Size: 18444 bytes
- Lines: 701
- Exports: None

### frontend/scripts/role-screenshot-audit.py
- Size: 12755 bytes
- Lines: 333
- Classes: RoleAudit
- Functions: None

### frontend/src/api/__tests__/client.test.ts
- Size: 2000 bytes
- Lines: 73
- Exports: None

### frontend/src/api/accounts.ts
- Size: 3533 bytes
- Lines: 137
- Exports: accountApi

### frontend/src/api/analytics.ts
- Size: 798 bytes
- Lines: 34
- Exports: analyticsApi

### frontend/src/api/andon.ts
- Size: 1282 bytes
- Lines: 33
- Exports: andonApi

### frontend/src/api/auth.ts
- Size: 6179 bytes
- Lines: 262
- Exports: authApi, usersApi

### frontend/src/api/client.ts
- Size: 7652 bytes
- Lines: 286
- Exports: createAbortController, isAbortError, apiClient

### frontend/src/api/executive.ts
- Size: 1508 bytes
- Lines: 61
- Exports: executiveApi

### frontend/src/api/index.ts
- Size: 790 bytes
- Lines: 9
- Exports: None

### frontend/src/api/maintenance.ts
- Size: 1539 bytes
- Lines: 62
- Exports: maintenanceApi

### frontend/src/api/production.ts
- Size: 3555 bytes
- Lines: 142
- Exports: productionApi

### frontend/src/api/products.ts
- Size: 1528 bytes
- Lines: 56
- Exports: productApi

### frontend/src/api/quality.ts
- Size: 11156 bytes
- Lines: 441
- Exports: inspectionApi, ncrApi, capaApi, qualityApi

### frontend/src/api/rfq.ts
- Size: 11575 bytes
- Lines: 494
- Exports: rfqApi, quoteApi

### frontend/src/api/supply-chain.ts
- Size: 896 bytes
- Lines: 36
- Exports: supplyChainApi

### frontend/src/api/task.ts
- Size: 8167 bytes
- Lines: 338
- Exports: taskApi, kanbanApi

### frontend/src/api/today.ts
- Size: 544 bytes
- Lines: 21
- Exports: todayApi

### frontend/src/app/(auth)/error.tsx
- Size: 1987 bytes
- Lines: 58
- Exports: AuthError

### frontend/src/app/(auth)/forgot-password/page.tsx
- Size: 4626 bytes
- Lines: 124
- Exports: ForgotPasswordPage

### frontend/src/app/(auth)/layout.tsx
- Size: 2256 bytes
- Lines: 55
- Exports: AuthLayout

### frontend/src/app/(auth)/loading.tsx
- Size: 421 bytes
- Lines: 13
- Exports: AuthLoading

### frontend/src/app/(auth)/login/page.tsx
- Size: 6057 bytes
- Lines: 162
- Exports: LoginPage

### frontend/src/app/(auth)/register/page.tsx
- Size: 5830 bytes
- Lines: 157
- Exports: RegisterPage

### frontend/src/app/(dashboard)/(admin)/admin/page.tsx
- Size: 47088 bytes
- Lines: 1097
- Exports: AdminPage

### frontend/src/app/(dashboard)/(admin)/layout.tsx
- Size: 259 bytes
- Lines: 16
- Exports: AdminLayout

### frontend/src/app/(dashboard)/(ops)/a3/[id]/edit/page.tsx
- Size: 6341 bytes
- Lines: 163
- Exports: EditA3Page

### frontend/src/app/(dashboard)/(ops)/a3/[id]/page.tsx
- Size: 6957 bytes
- Lines: 188
- Exports: A3DetailsPage

### frontend/src/app/(dashboard)/(ops)/a3/new/page.tsx
- Size: 7336 bytes
- Lines: 230
- Exports: NewA3Page

### frontend/src/app/(dashboard)/(ops)/a3/page.tsx
- Size: 15527 bytes
- Lines: 416
- Exports: A3Page

### frontend/src/app/(dashboard)/(ops)/ctq/[id]/page.tsx
- Size: 25740 bytes
- Lines: 726
- Exports: CTQDetailPage

### frontend/src/app/(dashboard)/(ops)/ctq/page.tsx
- Size: 21155 bytes
- Lines: 561
- Exports: CTQPage

### frontend/src/app/(dashboard)/(ops)/exceptions/page.tsx
- Size: 22472 bytes
- Lines: 547
- Exports: ExceptionsPage

### frontend/src/app/(dashboard)/(ops)/layout.tsx
- Size: 304 bytes
- Lines: 17
- Exports: OpsLayout

### frontend/src/app/(dashboard)/(ops)/obeya/[id]/page.tsx
- Size: 26372 bytes
- Lines: 759
- Exports: ObeyaItemDetailPage

### frontend/src/app/(dashboard)/(ops)/obeya/new/page.tsx
- Size: 5292 bytes
- Lines: 136
- Exports: NewObeyaBoardPage

### frontend/src/app/(dashboard)/(ops)/obeya/page.tsx
- Size: 20502 bytes
- Lines: 456
- Exports: ObeyaPage

### frontend/src/app/(dashboard)/(ops)/ops/page.tsx
- Size: 12187 bytes
- Lines: 379
- Exports: TodayPage

### frontend/src/app/(dashboard)/(sales)/__tests__/page-refined.test.tsx
- Size: 18620 bytes
- Lines: 583
- Exports: None

### frontend/src/app/(dashboard)/(sales)/customers/[id]/page.tsx
- Size: 21424 bytes
- Lines: 593
- Exports: CustomerDetailPage

### frontend/src/app/(dashboard)/(sales)/customers/new/page.tsx
- Size: 20220 bytes
- Lines: 622
- Exports: CustomerFormPage

### frontend/src/app/(dashboard)/(sales)/customers/page.tsx
- Size: 16554 bytes
- Lines: 433
- Exports: CustomersPage

### frontend/src/app/(dashboard)/(sales)/layout.tsx
- Size: 310 bytes
- Lines: 17
- Exports: SalesLayout

### frontend/src/app/(dashboard)/(sales)/page-refined.tsx
- Size: 26923 bytes
- Lines: 774
- Exports: PipelinePage

### frontend/src/app/(dashboard)/(sales)/quotes/[id]/page.tsx
- Size: 24022 bytes
- Lines: 632
- Exports: QuoteDetailPage

### frontend/src/app/(dashboard)/(sales)/quotes/new/page-refined.tsx
- Size: 42767 bytes
- Lines: 1161
- Exports: NewQuotePageRefined

### frontend/src/app/(dashboard)/(sales)/quotes/new/page.tsx
- Size: 22441 bytes
- Lines: 627
- Exports: NewQuotePage

### frontend/src/app/(dashboard)/(sales)/quotes/page.tsx
- Size: 14269 bytes
- Lines: 395
- Exports: QuotesPage

### frontend/src/app/(dashboard)/(sales)/sales/page.tsx
- Size: 17144 bytes
- Lines: 467
- Exports: PipelinePage

### frontend/src/app/(dashboard)/(shop-floor)/andon/analytics/page.tsx
- Size: 6129 bytes
- Lines: 162
- Exports: AndonAnalyticsPage

### frontend/src/app/(dashboard)/(shop-floor)/andon/history/page.tsx
- Size: 4099 bytes
- Lines: 104
- Exports: AndonHistoryPage

### frontend/src/app/(dashboard)/(shop-floor)/andon/page.tsx
- Size: 10757 bytes
- Lines: 294
- Exports: AndonBoardPage

### frontend/src/app/(dashboard)/(shop-floor)/andon/reports/page.tsx
- Size: 3201 bytes
- Lines: 89
- Exports: AndonReportsPage

### frontend/src/app/(dashboard)/(shop-floor)/andon/settings/page.tsx
- Size: 4645 bytes
- Lines: 117
- Exports: AndonSettingsPage

### frontend/src/app/(dashboard)/(shop-floor)/layout.tsx
- Size: 310 bytes
- Lines: 17
- Exports: ShopFloorLayout

### frontend/src/app/(dashboard)/(shop-floor)/maintenance/page.tsx
- Size: 11567 bytes
- Lines: 320
- Exports: MaintenancePage

### frontend/src/app/(dashboard)/(shop-floor)/production/[id]/page.tsx
- Size: 10692 bytes
- Lines: 246
- Exports: WorkOrderDetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/production/new/page.tsx
- Size: 6744 bytes
- Lines: 195
- Exports: NewWorkOrderPage

### frontend/src/app/(dashboard)/(shop-floor)/production/page.tsx
- Size: 18331 bytes
- Lines: 482
- Exports: ProductionPage

### frontend/src/app/(dashboard)/(shop-floor)/products/[id]/edit/page.tsx
- Size: 8481 bytes
- Lines: 216
- Exports: EditProductPage

### frontend/src/app/(dashboard)/(shop-floor)/products/[id]/page.tsx
- Size: 25016 bytes
- Lines: 665
- Exports: ProductDetailPage

### frontend/src/app/(dashboard)/(shop-floor)/products/new/page.tsx
- Size: 10148 bytes
- Lines: 267
- Exports: NewProductPage

### frontend/src/app/(dashboard)/(shop-floor)/products/page.tsx
- Size: 16088 bytes
- Lines: 413
- Exports: ProductsPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/analytics/page.tsx
- Size: 7511 bytes
- Lines: 193
- Exports: QualityAnalyticsPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/capas/[id]/page.tsx
- Size: 10091 bytes
- Lines: 234
- Exports: CAPADetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/capas/new/page.tsx
- Size: 5426 bytes
- Lines: 145
- Exports: NewCAPAPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/inspections/[id]/page.tsx
- Size: 8714 bytes
- Lines: 211
- Exports: InspectionDetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/inspections/new/page.tsx
- Size: 5089 bytes
- Lines: 133
- Exports: NewInspectionPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/ncrs/[id]/page.tsx
- Size: 9011 bytes
- Lines: 223
- Exports: NCRDetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/ncrs/new/page.tsx
- Size: 6336 bytes
- Lines: 184
- Exports: NewNCRPage

### frontend/src/app/(dashboard)/(shop-floor)/quality/page.tsx
- Size: 27286 bytes
- Lines: 666
- Exports: QualityPage

### frontend/src/app/(dashboard)/(shop-floor)/training/certifications/[id]/page.tsx
- Size: 4045 bytes
- Lines: 95
- Exports: CertificationDetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/training/certifications/new/page.tsx
- Size: 3454 bytes
- Lines: 92
- Exports: NewCertificationPage

### frontend/src/app/(dashboard)/(shop-floor)/training/enroll/page.tsx
- Size: 3195 bytes
- Lines: 85
- Exports: EnrollTrainingPage

### frontend/src/app/(dashboard)/(shop-floor)/training/matrix/page.tsx
- Size: 7514 bytes
- Lines: 174
- Exports: TrainingMatrixPage

### frontend/src/app/(dashboard)/(shop-floor)/training/page.tsx
- Size: 22348 bytes
- Lines: 591
- Exports: TrainingPage

### frontend/src/app/(dashboard)/(shop-floor)/training/programs/[id]/page.tsx
- Size: 5156 bytes
- Lines: 126
- Exports: ProgramDetailsPage

### frontend/src/app/(dashboard)/(shop-floor)/training/programs/new/page.tsx
- Size: 4893 bytes
- Lines: 138
- Exports: NewProgramPage

### frontend/src/app/(dashboard)/__tests__/navigation-flow.test.tsx
- Size: 29140 bytes
- Lines: 896
- Exports: None

### frontend/src/app/(dashboard)/__tests__/pipeline.test.tsx
- Size: 18108 bytes
- Lines: 550
- Exports: None

### frontend/src/app/(dashboard)/__tests__/rfq-detail.test.tsx
- Size: 22223 bytes
- Lines: 634
- Exports: None

### frontend/src/app/(dashboard)/__tests__/today.test.tsx
- Size: 15430 bytes
- Lines: 461
- Exports: None

### frontend/src/app/(dashboard)/analytics/page.tsx
- Size: 27549 bytes
- Lines: 531
- Exports: AnalyticsPage

### frontend/src/app/(dashboard)/auditor/page.tsx
- Size: 13225 bytes
- Lines: 360
- Exports: AuditorDashboard

### frontend/src/app/(dashboard)/error.tsx
- Size: 2607 bytes
- Lines: 76
- Exports: DashboardError

### frontend/src/app/(dashboard)/executive/page.tsx
- Size: 22349 bytes
- Lines: 412
- Exports: ExecutivePage

### frontend/src/app/(dashboard)/finance/page.tsx
- Size: 5955 bytes
- Lines: 154
- Exports: FinancePage

### frontend/src/app/(dashboard)/hr/page.tsx
- Size: 9471 bytes
- Lines: 282
- Exports: HRDashboard

### frontend/src/app/(dashboard)/it/page.tsx
- Size: 13809 bytes
- Lines: 388
- Exports: ITDashboard

### frontend/src/app/(dashboard)/layout.tsx
- Size: 1690 bytes
- Lines: 63
- Exports: DashboardLayout

### frontend/src/app/(dashboard)/loading.tsx
- Size: 3330 bytes
- Lines: 92
- Exports: DashboardLoading

### frontend/src/app/(dashboard)/pipeline/[id]/page.tsx
- Size: 22131 bytes
- Lines: 585
- Exports: RFQDetailPage

### frontend/src/app/(dashboard)/pipeline/new/page.tsx
- Size: 13676 bytes
- Lines: 387
- Exports: NewRFQPage

### frontend/src/app/(dashboard)/pipeline/page.tsx
- Size: 13112 bytes
- Lines: 346
- Exports: PipelinePage

### frontend/src/app/(dashboard)/project-management/[id]/_components/backlog-view.tsx
- Size: 25158 bytes
- Lines: 580
- Exports: BacklogView

### frontend/src/app/(dashboard)/project-management/[id]/_components/epics-list.tsx
- Size: 6024 bytes
- Lines: 147
- Exports: EpicsList

### frontend/src/app/(dashboard)/project-management/[id]/_components/issues-list.tsx
- Size: 15482 bytes
- Lines: 354
- Exports: IssuesList

### frontend/src/app/(dashboard)/project-management/[id]/_components/kanban-board.tsx
- Size: 5050 bytes
- Lines: 160
- Exports: KanbanBoard

### frontend/src/app/(dashboard)/project-management/[id]/_components/milestones-list.tsx
- Size: 8820 bytes
- Lines: 217
- Exports: MilestonesList

### frontend/src/app/(dashboard)/project-management/[id]/_components/project-activity.tsx
- Size: 4516 bytes
- Lines: 102
- Exports: ProjectActivityTimeline

### frontend/src/app/(dashboard)/project-management/[id]/_components/project-dashboard.tsx
- Size: 7994 bytes
- Lines: 187
- Exports: ProjectDashboard

### frontend/src/app/(dashboard)/project-management/[id]/_components/project-settings.tsx
- Size: 6194 bytes
- Lines: 159
- Exports: ProjectSettings

### frontend/src/app/(dashboard)/project-management/[id]/_components/sprint-list.tsx
- Size: 8149 bytes
- Lines: 211
- Exports: SprintList

### frontend/src/app/(dashboard)/project-management/[id]/_components/wiki-view.tsx
- Size: 7554 bytes
- Lines: 197
- Exports: WikiView

### frontend/src/app/(dashboard)/project-management/[id]/page.tsx
- Size: 8295 bytes
- Lines: 199
- Exports: ProjectDetailPage

### frontend/src/app/(dashboard)/project-management/page.tsx
- Size: 15178 bytes
- Lines: 364
- Exports: ProjectManagementPage

### frontend/src/app/(dashboard)/projects/[id]/page.tsx
- Size: 62 bytes
- Lines: 2
- Exports: None

### frontend/src/app/(dashboard)/projects/page.tsx
- Size: 54 bytes
- Lines: 2
- Exports: None

### frontend/src/app/(dashboard)/rfqs/[id]/page.tsx
- Size: 52 bytes
- Lines: 2
- Exports: None

### frontend/src/app/(dashboard)/rfqs/new/page.tsx
- Size: 51 bytes
- Lines: 2
- Exports: None

### frontend/src/app/(dashboard)/rfqs/page.tsx
- Size: 44 bytes
- Lines: 2
- Exports: None

### frontend/src/app/(dashboard)/settings/(admin-only)/api/page.tsx
- Size: 1897 bytes
- Lines: 46
- Exports: ApiSettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/company/page.tsx
- Size: 1050 bytes
- Lines: 29
- Exports: CompanySettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/data/page.tsx
- Size: 1485 bytes
- Lines: 35
- Exports: DataSettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/email/page.tsx
- Size: 955 bytes
- Lines: 28
- Exports: EmailSettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/integrations/page.tsx
- Size: 1552 bytes
- Lines: 34
- Exports: IntegrationsSettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/layout.tsx
- Size: 267 bytes
- Lines: 16
- Exports: AdminSettingsLayout

### frontend/src/app/(dashboard)/settings/(admin-only)/mobile/page.tsx
- Size: 1078 bytes
- Lines: 29
- Exports: MobileSettingsPage

### frontend/src/app/(dashboard)/settings/(admin-only)/team/page.tsx
- Size: 15857 bytes
- Lines: 407
- Exports: TeamSettingsPage

### frontend/src/app/(dashboard)/settings/account/page.tsx
- Size: 1183 bytes
- Lines: 34
- Exports: AccountSettingsPage

### frontend/src/app/(dashboard)/settings/appearance/page.tsx
- Size: 14216 bytes
- Lines: 384
- Exports: AppearanceSettingsPage

### frontend/src/app/(dashboard)/settings/language/page.tsx
- Size: 1540 bytes
- Lines: 42
- Exports: LanguageSettingsPage

### frontend/src/app/(dashboard)/settings/layout.tsx
- Size: 3669 bytes
- Lines: 99
- Exports: SettingsLayout

### frontend/src/app/(dashboard)/settings/notifications/page.tsx
- Size: 13999 bytes
- Lines: 413
- Exports: NotificationsSettingsPage

### frontend/src/app/(dashboard)/settings/page.tsx
- Size: 10234 bytes
- Lines: 256
- Exports: SettingsPage

### frontend/src/app/(dashboard)/settings/profile/page.tsx
- Size: 10745 bytes
- Lines: 298
- Exports: ProfileSettingsPage

### frontend/src/app/(dashboard)/settings/security/page.tsx
- Size: 16676 bytes
- Lines: 429
- Exports: SecuritySettingsPage

### frontend/src/app/(dashboard)/supply-chain/page.tsx
- Size: 7431 bytes
- Lines: 202
- Exports: SupplyChainPage

### frontend/src/app/(dashboard)/tasks/new/page.tsx
- Size: 4318 bytes
- Lines: 122
- Exports: NewTaskPage

### frontend/src/app/(dashboard)/tasks/page.tsx
- Size: 9292 bytes
- Lines: 242
- Exports: TasksPage

### frontend/src/app/(dashboard)/today/_components/my-work-dashboard.tsx
- Size: 3976 bytes
- Lines: 89
- Exports: MyWorkDashboard

### frontend/src/app/(dashboard)/today/page.tsx
- Size: 17597 bytes
- Lines: 475
- Exports: TodayPage

### frontend/src/app/(dashboard)/warehouse/page.tsx
- Size: 9713 bytes
- Lines: 278
- Exports: WarehouseDashboard

### frontend/src/app/api/health/route.ts
- Size: 210 bytes
- Lines: 12
- Exports: runtime

### frontend/src/app/globals.css
- Size: 4489 bytes
- Lines: 146
- Snippet: @tailwind base;

### frontend/src/app/layout.tsx
- Size: 1669 bytes
- Lines: 62
- Exports: metadata, viewport, RootLayout

### frontend/src/app/offline/page.tsx
- Size: 2029 bytes
- Lines: 55
- Exports: OfflinePage

### frontend/src/app/providers.tsx
- Size: 2353 bytes
- Lines: 76
- Exports: Providers

### frontend/src/components/CorrectionUI.tsx
- Size: 28514 bytes
- Lines: 984
- Exports: inferCorrectionType, calculateConfidence, CorrectionButton, CorrectionModal, InlineCorrection, useCorrectionSubmit, CorrectionProvider, useCorrectionContext

### frontend/src/components/__tests__/CorrectionUI.test.tsx
- Size: 24504 bytes
- Lines: 800
- Exports: None

### frontend/src/components/__tests__/responsive.test.tsx
- Size: 19762 bytes
- Lines: 701
- Exports: None

### frontend/src/components/andon/__tests__/andon-dashboard.test.tsx
- Size: 29165 bytes
- Lines: 888
- Exports: None

### frontend/src/components/andon/andon-dashboard.tsx
- Size: 27726 bytes
- Lines: 781
- Exports: AndonDashboardHeader, AndonMetricsBar, AndonEventCard, AndonEventList, WorkCenterStatusCard, AndonFilterBar, AndonDashboard

### frontend/src/components/coming-soon.tsx
- Size: 1202 bytes
- Lines: 39
- Exports: ComingSoon

### frontend/src/components/command-palette/__tests__/command-palette.test.tsx
- Size: 26362 bytes
- Lines: 850
- Exports: None

### frontend/src/components/command-palette/command-palette.tsx
- Size: 20755 bytes
- Lines: 589
- Exports: CommandPalette

### frontend/src/components/command-palette/index.ts
- Size: 114 bytes
- Lines: 3
- Exports: None

### frontend/src/components/email/__tests__/email-composer.test.tsx
- Size: 32542 bytes
- Lines: 954
- Exports: None

### frontend/src/components/email/email-composer.tsx
- Size: 32809 bytes
- Lines: 998
- Exports: PurposeSelector, ToneSelector, LanguageSelector, RecipientInput, KeyPointsEditor, DraftPreview, CompliancePanel, SuggestionsPanel, AlternativeSubjects, EmailComposer, DraftListItem, DraftsList

### frontend/src/components/kanban/__tests__/kanban-board.test.tsx
- Size: 16228 bytes
- Lines: 530
- Exports: None

### frontend/src/components/kanban/kanban-board.tsx
- Size: 21179 bytes
- Lines: 686
- Exports: KanbanBoard, KanbanToolbar, KanbanMetrics

### frontend/src/components/layout/__tests__/sidebar.test.tsx
- Size: 3160 bytes
- Lines: 93
- Exports: None

### frontend/src/components/layout/command-palette.tsx
- Size: 8377 bytes
- Lines: 243
- Exports: CommandPalette

### frontend/src/components/layout/index.ts
- Size: 109 bytes
- Lines: 3
- Exports: None

### frontend/src/components/layout/mobile-nav.tsx
- Size: 5557 bytes
- Lines: 183
- Exports: MobileBottomNav, MobileDrawerOverlay, useMobileNav

### frontend/src/components/layout/page-guard.tsx
- Size: 2997 bytes
- Lines: 102
- Exports: PageGuard, useUserRoles, useCanViewFinancials, useIsAdmin

### frontend/src/components/layout/sidebar.tsx
- Size: 16607 bytes
- Lines: 461
- Exports: Sidebar, Header, MainLayout

### frontend/src/components/onboarding/index.ts
- Size: 367 bytes
- Lines: 17
- Exports: None

### frontend/src/components/onboarding/tour.tsx
- Size: 8953 bytes
- Lines: 343
- Exports: TourProvider, useTour, TourOverlay

### frontend/src/components/onboarding/types.ts
- Size: 3657 bytes
- Lines: 167
- Exports: TOUR_POSITION, ONBOARDING_STATE, HELP_CATEGORY, EMPTY_STATE_TYPE, SUGGESTION_TYPE

### frontend/src/components/pdf-preview/__tests__/pdf-preview.test.tsx
- Size: 22634 bytes
- Lines: 722
- Exports: None

### frontend/src/components/pdf-preview/index.ts
- Size: 562 bytes
- Lines: 27
- Exports: None

### frontend/src/components/pdf-preview/pdf-preview.tsx
- Size: 29434 bytes
- Lines: 870
- Exports: PDFPreview

### frontend/src/components/pwa/__tests__/pwa-provider.test.tsx
- Size: 1066 bytes
- Lines: 45
- Exports: None

### frontend/src/components/pwa/pwa-provider.tsx
- Size: 3956 bytes
- Lines: 152
- Exports: PWAProvider

### frontend/src/components/quick-actions/__tests__/quick-actions-bar.test.tsx
- Size: 23922 bytes
- Lines: 708
- Exports: None

### frontend/src/components/quick-actions/quick-actions-bar.tsx
- Size: 16189 bytes
- Lines: 563
- Exports: QuickActionsBar, QuickActionsCompact, QuickActionsFloating, QuickActionsToolbar, useQuickActionShortcuts

### frontend/src/components/scanner/__tests__/barcode-scanner.test.tsx
- Size: 14648 bytes
- Lines: 508
- Exports: None

### frontend/src/components/scanner/barcode-scanner.tsx
- Size: 15504 bytes
- Lines: 488
- Exports: BarcodeScanner, ScannerModal, ScanButton

### frontend/src/components/settings-page-shell.tsx
- Size: 1411 bytes
- Lines: 49
- Exports: SettingsPageShell

### frontend/src/components/sync/__tests__/sync-status.test.tsx
- Size: 12479 bytes
- Lines: 448
- Exports: None

### frontend/src/components/sync/sync-status.tsx
- Size: 11207 bytes
- Lines: 416
- Exports: SyncStatusIndicator, SyncStatusBanner, PendingOperationsList

### frontend/src/components/ui/__tests__/accessibility.test.tsx
- Size: 28104 bytes
- Lines: 895
- Exports: None

### frontend/src/components/ui/__tests__/avatar.test.tsx
- Size: 3732 bytes
- Lines: 112
- Exports: None

### frontend/src/components/ui/__tests__/badge.test.tsx
- Size: 2265 bytes
- Lines: 62
- Exports: None

### frontend/src/components/ui/__tests__/browser-interop.test.tsx
- Size: 29487 bytes
- Lines: 1083
- Exports: None

### frontend/src/components/ui/__tests__/button.test.tsx
- Size: 2906 bytes
- Lines: 88
- Exports: None

### frontend/src/components/ui/__tests__/card.test.tsx
- Size: 3686 bytes
- Lines: 112
- Exports: None

### frontend/src/components/ui/__tests__/checkbox.test.tsx
- Size: 3752 bytes
- Lines: 120
- Exports: None

### frontend/src/components/ui/__tests__/data-visualization.test.tsx
- Size: 30625 bytes
- Lines: 992
- Exports: None

### frontend/src/components/ui/__tests__/deployment-maturity.test.tsx
- Size: 37977 bytes
- Lines: 1167
- Exports: None

### frontend/src/components/ui/__tests__/design-system.test.tsx
- Size: 38307 bytes
- Lines: 1181
- Exports: None

### frontend/src/components/ui/__tests__/empty-state.test.tsx
- Size: 12249 bytes
- Lines: 377
- Exports: None

### frontend/src/components/ui/__tests__/error-experience.test.tsx
- Size: 27696 bytes
- Lines: 937
- Exports: None

### frontend/src/components/ui/__tests__/factory-floor.test.tsx
- Size: 28716 bytes
- Lines: 941
- Exports: None

### frontend/src/components/ui/__tests__/input.test.tsx
- Size: 2876 bytes
- Lines: 87
- Exports: None

### frontend/src/components/ui/__tests__/label.test.tsx
- Size: 2267 bytes
- Lines: 67
- Exports: None

### frontend/src/components/ui/__tests__/motion-feedback.test.tsx
- Size: 31805 bytes
- Lines: 1015
- Exports: None

### frontend/src/components/ui/__tests__/onboarding-help.test.tsx
- Size: 32351 bytes
- Lines: 1211
- Exports: None

### frontend/src/components/ui/__tests__/performance-rum.test.tsx
- Size: 32595 bytes
- Lines: 1093
- Exports: None

### frontend/src/components/ui/__tests__/print-export.test.tsx
- Size: 25861 bytes
- Lines: 974
- Exports: None

### frontend/src/components/ui/__tests__/security-privacy.test.tsx
- Size: 26179 bytes
- Lines: 848
- Exports: None

### frontend/src/components/ui/__tests__/session-management.test.tsx
- Size: 34268 bytes
- Lines: 1230
- Exports: None

### frontend/src/components/ui/__tests__/skeleton.test.tsx
- Size: 11381 bytes
- Lines: 338
- Exports: None

### frontend/src/components/ui/__tests__/spatial-ui.test.tsx
- Size: 49130 bytes
- Lines: 1574
- Exports: None

### frontend/src/components/ui/__tests__/switch.test.tsx
- Size: 3675 bytes
- Lines: 120
- Exports: None

### frontend/src/components/ui/__tests__/table.test.tsx
- Size: 14760 bytes
- Lines: 523
- Exports: None

### frontend/src/components/ui/__tests__/textarea.test.tsx
- Size: 3815 bytes
- Lines: 103
- Exports: None

### frontend/src/components/ui/__tests__/timeline.test.tsx
- Size: 16930 bytes
- Lines: 593
- Exports: None

### frontend/src/components/ui/accessibility.tsx
- Size: 22517 bytes
- Lines: 807
- Exports: MIN_TOUCH_TARGET, FOCUS_RING_WIDTH, KEYBOARD_KEYS, ARIA_LIVE, SkipToContent, FocusTrap, AriaLiveRegion, VisuallyHidden, MainLandmark, NavLandmark, AsideLandmark, HeaderLandmark, FooterLandmark, RegionLandmark, AccessibleIconButton, HighContrastProvider, useReducedMotion, ReducedMotionAware, useKeyboardNavigation, TabOrderManager

### frontend/src/components/ui/alert-dialog.tsx
- Size: 4443 bytes
- Lines: 141
- Exports: None

### frontend/src/components/ui/alert.tsx
- Size: 1597 bytes
- Lines: 60
- Exports: None

### frontend/src/components/ui/avatar.tsx
- Size: 5028 bytes
- Lines: 179
- Exports: None

### frontend/src/components/ui/badge.tsx
- Size: 2545 bytes
- Lines: 66
- Exports: None

### frontend/src/components/ui/browser-interop.tsx
- Size: 38095 bytes
- Lines: 1296
- Exports: BROWSER, OS, LOCALE, UNIT_SYSTEM, THEME_MODE, TEXT_DIRECTION, CSS_FEATURE, detectBrowser, detectOS, isTouchDevice, isMobileDevice, checkCSSFeature, getCSSFeatureSupport, canShare, canShareFiles, ThemeProvider, useTheme, ThemeToggle, ScrollbarContainer, getTextDirection

### frontend/src/components/ui/button.tsx
- Size: 3406 bytes
- Lines: 97
- Exports: None

### frontend/src/components/ui/calendar.tsx
- Size: 5511 bytes
- Lines: 188
- Exports: Calendar

### frontend/src/components/ui/card.tsx
- Size: 2400 bytes
- Lines: 86
- Exports: None

### frontend/src/components/ui/checkbox.tsx
- Size: 1315 bytes
- Lines: 38
- Exports: None

### frontend/src/components/ui/collapsible.tsx
- Size: 360 bytes
- Lines: 13
- Exports: None

### frontend/src/components/ui/confirmation-dialog.tsx
- Size: 9080 bytes
- Lines: 335
- Exports: ConfirmationDialog, useConfirmation, useDeleteConfirmation, useBulkDeleteConfirmation, useDiscardChangesConfirmation

### frontend/src/components/ui/data-visualization.tsx
- Size: 29405 bytes
- Lines: 1067
- Exports: KPI_COLORS, CHART_TYPE, EXPORT_FORMAT, DrilldownProvider, useDrilldown, DrilldownBreadcrumbs, ChartTooltip, ChartLegend, Sparkline, BarChart, DonutChart, KPICard, ChartExportButton, generateDashboardUrl, parseDashboardUrl

### frontend/src/components/ui/deployment-maturity.tsx
- Size: 33289 bytes
- Lines: 1019
- Exports: MATURITY_LEVELS, MATURITY_LEVEL_NAMES, MATURITY_LEVEL_DESCRIPTIONS, FEATURE_REQUIREMENTS, isFeatureAvailable, getAvailableFeatures, getNextLevelFeatures, checkLevelUpRequirements, auditFeatureLeakage, runFullLeakageAudit, MaturityProvider, useMaturity, MaturityLevelIndicator, FeatureGate, LevelUpButton, RehearsalModeBanner, SandboxModeBanner, MaturityDashboard, createSATChecklist, updateSATChecklistItem

### frontend/src/components/ui/design-system.tsx
- Size: 37682 bytes
- Lines: 1286
- Exports: COLOR_TOKENS, SPACING_TOKENS, TYPOGRAPHY_TOKENS, RADIUS_TOKENS, SHADOW_TOKENS, ANIMATION_TOKENS, BREAKPOINT_TOKENS, validateCssVariable, auditColorTokens, getTokenValue, DesignSystemProvider, useDesignSystem, createComponentAudit, ColorSwatch, SpacingScale, TypographyScale, TokenDocumentation, VISUAL_WEIGHTS, useVisualWeight, INTERACTION_PATTERNS

### frontend/src/components/ui/dialog.tsx
- Size: 3950 bytes
- Lines: 127
- Exports: None

### frontend/src/components/ui/dropdown-menu.tsx
- Size: 7494 bytes
- Lines: 209
- Exports: None

### frontend/src/components/ui/empty-state.tsx
- Size: 18112 bytes
- Lines: 675
- Exports: EmptyState, RFQEmptyState, QuoteEmptyState, WorkOrderEmptyState, AccountEmptyState, ProductEmptyState, ContactEmptyState, AndonEmptyState, A3EmptyState, TrainingEmptyState, WorkCenterEmptyState, SearchEmptyState, FilterEmptyState, ErrorEmptyState, NotFoundEmptyState, TaskEmptyState, ExceptionEmptyState, ObeyaEmptyState, ProjectEmptyState, MaintenanceEmptyState

### frontend/src/components/ui/error-experience.tsx
- Size: 29324 bytes
- Lines: 1058
- Exports: ERROR_SEVERITY, OFFLINE_STATUS, CONFLICT_STRATEGY, ActionableError, FieldError, ServerErrorPage, EmptyState, EMPTY_STATE_PRESETS, OfflineBanner, ReadOnlyIndicator, SyncQueueIndicator, ConflictResolution, useNetworkStatus, OfflineProvider, useOfflineStatus, ErrorBoundary, formatValidationErrors, getFieldError, createActionableMessage, NotFoundPage

### frontend/src/components/ui/factory-floor.tsx
- Size: 32252 bytes
- Lines: 1146
- Exports: SHOP_FLOOR_THEME, TOUCH_TARGET, BARCODE_TYPE, VOICE_STATE, ShopFloorProvider, useShopFloor, HighGlareContainer, ShopFloorThemeToggle, GloveButton, GloveTouchTarget, BarcodeScanner, ScanFeedback, VoiceCommandListener, LargeStatusIndicator, AndonButton, AndonAlert, BatteryIndicator, GloveModeToggle, useHardwareScanner, useDeviceCapabilities

### frontend/src/components/ui/form-field.tsx
- Size: 8213 bytes
- Lines: 288
- Exports: FormField, FormFieldGroup, FormActions

### frontend/src/components/ui/gantt-chart.tsx
- Size: 5516 bytes
- Lines: 136
- Exports: GanttChart

### frontend/src/components/ui/input.tsx
- Size: 1319 bytes
- Lines: 35
- Exports: None

### frontend/src/components/ui/label.tsx
- Size: 1217 bytes
- Lines: 50
- Exports: None

### frontend/src/components/ui/motion-feedback.tsx
- Size: 31978 bytes
- Lines: 1297
- Exports: ANIMATION_DURATION, EASING, HAPTIC_PATTERN, Skeleton, SkeletonText, SkeletonCard, SkeletonTableRow, SkeletonAvatar, ProgressBar, StepProgress, AnimatedCheckmark, AnimatedCross, Spinner, PulsingDots, Pressable, HoverScale, OptimisticUIProvider, useOptimisticUI, SyncStatus, ProgressiveImage

### frontend/src/components/ui/onboarding-help.tsx
- Size: 41605 bytes
- Lines: 1433
- Exports: TOUR_POSITION, ONBOARDING_STATE, HELP_CATEGORY, EMPTY_STATE_TYPE, SUGGESTION_TYPE, TourProvider, useTour, TourOverlay, OnboardingProvider, useOnboarding, WelcomeModal, EmptyState, HelpTooltip, ContextualHelpPanel, SenseiSuggestionsProvider, useSenseiSuggestions, SenseiSuggestionCard, SenseiAssistant, KeyboardShortcutHint, FeatureSpotlight

### frontend/src/components/ui/performance-rum.tsx
- Size: 40903 bytes
- Lines: 1359
- Exports: WEB_VITALS_THRESHOLDS, PERFORMANCE_BUDGETS, rateMetric, rateInteraction, observeLCP, observeFID, observeCLS, observeINP, getTTFB, getFCP, observeResources, createInteractionTracker, RUMProvider, useRUM, WebVitalCard, WebVitalsDashboard, InteractionLatencyList, BudgetViolationAlert, PerformanceBudgetMeter, ResourceBudgetDashboard

### frontend/src/components/ui/popover.tsx
- Size: 1329 bytes
- Lines: 38
- Exports: None

### frontend/src/components/ui/print-export.tsx
- Size: 28296 bytes
- Lines: 1025
- Exports: EXPORT_FORMAT, EXPORT_STATE, LABEL_SIZE, DOCUMENT_TYPE, generateFilename, parseFilename, PrintProvider, usePrint, PrintableDocument, PrintButton, ExportProgressIndicator, ExportButton, LabelPreview, LabelPrinterDialog, PrintableTable, useExport

### frontend/src/components/ui/progress.tsx
- Size: 791 bytes
- Lines: 29
- Exports: None

### frontend/src/components/ui/responsive.tsx
- Size: 16619 bytes
- Lines: 657
- Exports: BREAKPOINTS, MAX_WIDTHS, TOUCH_TARGETS, getBreakpoint, isTouchDevice, hasNotch, getSafeAreaInsets, getDeviceInfo, useDeviceInfo, useResponsive, useBreakpointValue, useMediaQuery, usePrefersDarkMode, usePrefersReducedMotion, usePrefersHighContrast, ResponsiveProvider, ResponsiveContainer, ResponsiveGrid, VisibleAt, HiddenAt

### frontend/src/components/ui/scroll-area.tsx
- Size: 1665 bytes
- Lines: 49
- Exports: None

### frontend/src/components/ui/security-privacy.tsx
- Size: 33748 bytes
- Lines: 1116
- Exports: PERMISSION, ROLE, ROLE_PERMISSIONS, CONFIDENTIALITY, SYNC_STATUS, AUDIT_ACTION, RBACProvider, useRBAC, PermissionGate, MaskedData, PrivacyIndicator, ConfidentialityLabel, SenseiProcessing, AuditTrail, ChangeHistoryModal, DataClassificationBanner, SecureActionButton, SessionSecurity

### frontend/src/components/ui/select.tsx
- Size: 5841 bytes
- Lines: 170
- Exports: None

### frontend/src/components/ui/separator.tsx
- Size: 770 bytes
- Lines: 32
- Exports: None

### frontend/src/components/ui/session-management.tsx
- Size: 32450 bytes
- Lines: 1143
- Exports: SESSION_STATE, BROADCAST_MESSAGE_TYPE, TOAST_SEVERITY, NOTIFICATION_TYPE, SESSION_TIMEOUTS, TabSyncProvider, useTabSync, SessionManagerProvider, useSession, SessionTimeoutWarning, ReAuthModal, ToastProvider, useToast, ToastContainer, NotificationProvider, useNotifications, NotificationCenter, NotificationBell

### frontend/src/components/ui/sheet.tsx
- Size: 4303 bytes
- Lines: 141
- Exports: None

### frontend/src/components/ui/skeleton.tsx
- Size: 18435 bytes
- Lines: 611
- Exports: None

### frontend/src/components/ui/spatial-ui.tsx
- Size: 37599 bytes
- Lines: 1212
- Exports: CELL_STATUS, CELL_STATUS_COLORS, FactoryMapProvider, useFactoryMap, FactoryFloorMap, CellDetailPanel, GembaPathVisualizer, DEFAULT_WAR_ROOM_LAYOUT, WarRoomProvider, useWarRoom, WarRoomPanelContainer, WarRoomDashboard, KPIPanel, AlertsPanel, TimelinePanel, MapControls, CellStatusLegend

### frontend/src/components/ui/switch.tsx
- Size: 1197 bytes
- Lines: 33
- Exports: None

### frontend/src/components/ui/table.tsx
- Size: 11201 bytes
- Lines: 421
- Exports: None

### frontend/src/components/ui/tabs.tsx
- Size: 1994 bytes
- Lines: 56
- Exports: None

### frontend/src/components/ui/textarea.tsx
- Size: 1523 bytes
- Lines: 46
- Exports: None

### frontend/src/components/ui/timeline.tsx
- Size: 13321 bytes
- Lines: 453
- Exports: None

### frontend/src/components/ui/toast.tsx
- Size: 4937 bytes
- Lines: 130
- Exports: None

### frontend/src/components/ui/toaster.tsx
- Size: 792 bytes
- Lines: 36
- Exports: Toaster

### frontend/src/components/ui/tooltip.tsx
- Size: 1222 bytes
- Lines: 36
- Exports: None

### frontend/src/components/validation/__tests__/inline-validation.test.tsx
- Size: 25665 bytes
- Lines: 853
- Exports: None

### frontend/src/components/validation/inline-validation.tsx
- Size: 25046 bytes
- Lines: 775
- Exports: ValidationMessage, ValidationMessages, FieldWrapper, ValidatedInput, ValidatedTextarea, ValidatedSelect, ValidatedCheckbox, GateCheckDisplay, FormSummary, AutoField

### frontend/src/hooks/__tests__/use-camera-scanner.test.ts
- Size: 16002 bytes
- Lines: 581
- Exports: None

### frontend/src/hooks/__tests__/use-capacitor.test.ts
- Size: 26843 bytes
- Lines: 918
- Exports: None

### frontend/src/hooks/__tests__/use-keyboard-shortcuts.test.ts
- Size: 32992 bytes
- Lines: 1024
- Exports: None

### frontend/src/hooks/__tests__/use-performance.test.ts
- Size: 17084 bytes
- Lines: 583
- Exports: None

### frontend/src/hooks/__tests__/use-pwa.test.ts
- Size: 5193 bytes
- Lines: 174
- Exports: None

### frontend/src/hooks/__tests__/use-responsive.test.ts
- Size: 23256 bytes
- Lines: 814
- Exports: None

### frontend/src/hooks/__tests__/use-sync-engine.test.ts
- Size: 13407 bytes
- Lines: 449
- Exports: None

### frontend/src/hooks/use-api-error.ts
- Size: 4434 bytes
- Lines: 176
- Exports: useApiError, createQueryErrorHandler, withErrorHandling

### frontend/src/hooks/use-api.ts
- Size: 16160 bytes
- Lines: 608
- Exports: invalidateCache, clearCache, useApi, useMutation, usePaginatedApi, useInfiniteApi

### frontend/src/hooks/use-camera-scanner.ts
- Size: 16201 bytes
- Lines: 624
- Exports: isBarcodeDetectorSupported, useCameraScanner, parseManufacturingBarcode

### frontend/src/hooks/use-capacitor.ts
- Size: 27577 bytes
- Lines: 1018
- Exports: isNativeApp, getPlatform, useNativeCapabilities, useCamera, useFileSystem, usePushNotifications, useHaptics, useShare, useClipboard, useStatusBar, useBiometricAuth, useAppState

### frontend/src/hooks/use-keyboard-shortcuts.ts
- Size: 28767 bytes
- Lines: 994
- Exports: normalizeKey, parseShortcutString, formatShortcutSequence, matchesKey, sequencesMatch, useKeyboardShortcutsStore, useKeyboardShortcuts, useShortcut, useShortcutScope, useDisableShortcuts, useFormattedShortcuts, initializeKeyboardShortcuts

### frontend/src/hooks/use-lazy-load.ts
- Size: 5442 bytes
- Lines: 224
- Exports: useIntersectionObserver, useLazyImage, useLazyRender, useInfiniteScroll

### frontend/src/hooks/use-performance.ts
- Size: 14249 bytes
- Lines: 518
- Exports: useDebounce, useDebouncedCallback, useThrottledCallback, useIntersectionObserver, useLazyLoad, usePerformanceMonitor, usePerformanceMark, useDeepMemo, useVirtualScroll, useIdleCallback, usePreload, usePreloadImages

### frontend/src/hooks/use-pwa.ts
- Size: 6891 bytes
- Lines: 251
- Exports: usePWA, useIsPWA, usePushNotifications

### frontend/src/hooks/use-responsive.ts
- Size: 15697 bytes
- Lines: 595
- Exports: BREAKPOINTS, TOUCH_TARGETS, getBreakpoint, isTouchDevice, hasNotch, getSafeAreaInsets, getDeviceInfo, useResponsive, useBreakpointValue, useMediaQuery, useSafeArea, usePrefersDarkMode, usePrefersReducedMotion, usePrefersHighContrast, useCoarsePointer, useCanHover, useOrientation, useBreakpointUp, useBreakpointDown, useBreakpointBetween

### frontend/src/hooks/use-sync-engine.ts
- Size: 10041 bytes
- Lines: 431
- Exports: useSyncEngine, useOptimisticMutation

### frontend/src/hooks/use-toast.ts
- Size: 3835 bytes
- Lines: 189
- Exports: reducer

### frontend/src/lib/__tests__/design-tokens-context.test.tsx
- Size: 18477 bytes
- Lines: 642
- Exports: None

### frontend/src/lib/__tests__/design-tokens.test.ts
- Size: 23804 bytes
- Lines: 713
- Exports: None

### frontend/src/lib/__tests__/lineage-layout.test.ts
- Size: 1563 bytes
- Lines: 51
- Exports: None

### frontend/src/lib/__tests__/utils.test.ts
- Size: 4027 bytes
- Lines: 142
- Exports: None

### frontend/src/lib/__tests__/validation.test.ts
- Size: 28192 bytes
- Lines: 970
- Exports: None

### frontend/src/lib/design-tokens-context.tsx
- Size: 13483 bytes
- Lines: 480
- Exports: DesignTokensProvider, useDesignTokens, useTheme, useDensity, useSpacing, useRadius, useShadow, useColors, useComponentSizes, useStatusColors, useBadgeVariants, useElevation, useCssVar, getInitialTheme, themeScript, ThemeToggle, DensityToggle

### frontend/src/lib/design-tokens.ts
- Size: 22652 bytes
- Lines: 934
- Exports: neutral, primary, success, warning, danger, info, lightTheme, darkTheme, elevations, darkElevations, shadows, radii, spacing, fontFamily, fontSize, fontWeight, letterSpacing, lineHeight, zIndex, transitions

### frontend/src/lib/error-utils.ts
- Size: 4768 bytes
- Lines: 176
- Exports: getErrorMessage, isAbortError, isNetworkError, isAuthError, isForbiddenError, isNotFoundError, isValidationError, getErrorStatus, getErrorCode, getUserFriendlyErrorMessage

### frontend/src/lib/i18n.ts
- Size: 17039 bytes
- Lines: 567
- Exports: LOCALE_CONFIGS, DEFAULT_LOCALE, t, formatNumber, formatCurrency, formatDate, formatRelativeTime, getDirection, getAvailableLocales

### frontend/src/lib/lineage-layout.ts
- Size: 3468 bytes
- Lines: 135
- Exports: makeNodeKey, computeLineageLayout

### frontend/src/lib/navigation.ts
- Size: 4468 bytes
- Lines: 99
- Exports: NAV_SECTIONS, QUICK_ACTIONS

### frontend/src/lib/page-access.ts
- Size: 6003 bytes
- Lines: 181
- Exports: EXECUTIVE_ROLES, FINANCE_ROLES, SALES_ROLES, OPS_ROLES, QUALITY_ROLES, MAINTENANCE_ROLES, SUPPLY_CHAIN_ROLES, HR_ROLES, IT_ROLES, TRAINING_ROLES, ANALYTICS_ROLES, PAGE_ACCESS, hasPageAccess, getUnauthorizedRedirect, canViewFinancials, canEdit, isAdmin

### frontend/src/lib/performance.tsx
- Size: 7167 bytes
- Lines: 277
- Exports: lazyWithFallback, lazyNamed, debounce, throttle, memoize, memoizeLRU, generateSrcSet, getBlurPlaceholder, measureTime, useRenderCount, scheduleUpdate, createBatcher

### frontend/src/lib/routes.ts
- Size: 8737 bytes
- Lines: 268
- Exports: AUTH_ROUTES, DASHBOARD_ROUTES, PRODUCTION_ROUTES, SHOP_FLOOR_ROUTES, SALES_ROUTES, QUALITY_ROUTES, MAINTENANCE_ROUTES, OPS_ROUTES, INVENTORY_ROUTES, ADMIN_ROUTES, EXECUTIVE_ROUTES, HR_ROUTES, IT_ROUTES, AUDITOR_ROUTES, ROUTES, buildUrl, matchRoute, getBreadcrumbs

### frontend/src/lib/test-utils.tsx
- Size: 8112 bytes
- Lines: 286
- Exports: renderWithProviders, mockAuthUser, mockAdminUser, mockApiResponse, mockPaginatedResponse, waitForLoadingToFinish, createDeferred, createMockStore, isFocusable, getFocusableElements, cleanForSnapshot

### frontend/src/lib/utils.ts
- Size: 2805 bytes
- Lines: 106
- Exports: cn, formatDate, formatDateTime, formatRelativeTime, formatCurrency, formatNumber, formatPercentage, truncate, capitalize, slugify, debounce, generateId, getInitials

### frontend/src/lib/validation.ts
- Size: 22242 bytes
- Lines: 856
- Exports: required, minLength, maxLength, min, max, pattern, email, url, phone, validDate, futureDate, pastDate, custom, asyncValidator, when, warning, info, combineResults, debounceValidation, createFieldValidation

### frontend/src/services/__tests__/sync-service.test.ts
- Size: 6845 bytes
- Lines: 259
- Exports: None

### frontend/src/services/sync-service.ts
- Size: 10405 bytes
- Lines: 387
- Exports: isBackgroundSyncSupported, isPeriodicSyncSupported, getSerializedPendingOperations, SyncManager, getSyncManager

### frontend/src/stores/__tests__/admin-store.test.ts
- Size: 2617 bytes
- Lines: 80
- Exports: None

### frontend/src/stores/__tests__/andon-store.test.ts
- Size: 26142 bytes
- Lines: 793
- Exports: None

### frontend/src/stores/__tests__/auth-store.test.ts
- Size: 4549 bytes
- Lines: 150
- Exports: None

### frontend/src/stores/__tests__/command-palette-store.test.ts
- Size: 27064 bytes
- Lines: 795
- Exports: None

### frontend/src/stores/__tests__/email-drafting-store.test.ts
- Size: 35379 bytes
- Lines: 1152
- Exports: None

### frontend/src/stores/__tests__/exceptions-store.test.ts
- Size: 2006 bytes
- Lines: 60
- Exports: None

### frontend/src/stores/__tests__/form-validation-store.test.ts
- Size: 25837 bytes
- Lines: 802
- Exports: None

### frontend/src/stores/__tests__/hr-store.test.ts
- Size: 1812 bytes
- Lines: 59
- Exports: None

### frontend/src/stores/__tests__/kanban-store.test.ts
- Size: 16442 bytes
- Lines: 553
- Exports: None

### frontend/src/stores/__tests__/pdf-preview-store.test.ts
- Size: 21641 bytes
- Lines: 631
- Exports: None

### frontend/src/stores/__tests__/pipeline-store.test.ts
- Size: 3374 bytes
- Lines: 110
- Exports: None

### frontend/src/stores/__tests__/quick-actions-store.test.ts
- Size: 26896 bytes
- Lines: 846
- Exports: None

### frontend/src/stores/__tests__/sync-store.test.ts
- Size: 18081 bytes
- Lines: 659
- Exports: None

### frontend/src/stores/a3.ts
- Size: 12070 bytes
- Lines: 408
- Exports: useA3Store

### frontend/src/stores/admin.ts
- Size: 25144 bytes
- Lines: 795
- Exports: useAdminStore

### frontend/src/stores/analytics.ts
- Size: 1404 bytes
- Lines: 53
- Exports: useAnalyticsStore

### frontend/src/stores/andon-store.ts
- Size: 21902 bytes
- Lines: 741
- Exports: useAndonStore, getSeverityColor, getSeverityLabel, getAndonTypeLabel, getAndonTypeIcon, getStatusLabel, getStatusColor, formatElapsedTime, formatDuration, calculateEscalationLevel

### frontend/src/stores/auth-store.ts
- Size: 4185 bytes
- Lines: 161
- Exports: useAuthStore

### frontend/src/stores/command-palette-store.ts
- Size: 19332 bytes
- Lines: 701
- Exports: useCommandPaletteStore, selectIsOpen, selectQuery, selectFilteredCommands, selectSelectedIndex, selectSelectedCommand, selectIsExecuting, useCommandPalette

### frontend/src/stores/ctq.ts
- Size: 10039 bytes
- Lines: 314
- Exports: useCTQStore

### frontend/src/stores/customers.ts
- Size: 1942 bytes
- Lines: 69
- Exports: useCustomersStore

### frontend/src/stores/email-drafting-store.ts
- Size: 28493 bytes
- Lines: 930
- Exports: generateId, getPurposeLabel, getToneLabel, getLanguageLabel, getStatusLabel, getStatusColor, getComplianceSeverityColor, getSuggestionPriorityColor, formatConfidenceScore, getConfidenceColor, formatGenerationTime, createDefaultContext, validateRecipient, createRecipient, useEmailDraftingStore

### frontend/src/stores/exceptions.ts
- Size: 10279 bytes
- Lines: 332
- Exports: useExceptionsStore

### frontend/src/stores/executive.ts
- Size: 1513 bytes
- Lines: 52
- Exports: useExecutiveStore

### frontend/src/stores/form-validation-store.ts
- Size: 23067 bytes
- Lines: 742
- Exports: useFormValidationStore, useForm, useField

### frontend/src/stores/hr.ts
- Size: 2185 bytes
- Lines: 84
- Exports: useHRStore

### frontend/src/stores/index.ts
- Size: 887 bytes
- Lines: 20
- Exports: None

### frontend/src/stores/kanban-store.ts
- Size: 17590 bytes
- Lines: 640
- Exports: useKanbanStore, getPriorityColor, formatCurrency, getDaysUntilDue, getDueDateStatus

### frontend/src/stores/maintenance.ts
- Size: 1382 bytes
- Lines: 53
- Exports: useMaintenanceStore

### frontend/src/stores/obeya.ts
- Size: 16871 bytes
- Lines: 554
- Exports: useObeyaStore

### frontend/src/stores/pdf-preview-store.ts
- Size: 10775 bytes
- Lines: 407
- Exports: ZOOM_LEVELS, MIN_ZOOM, MAX_ZOOM, DEFAULT_ZOOM, ZOOM_STEP, usePDFPreviewStore, selectSelectedVersion, selectVersionCount, selectCanGoNext, selectCanGoPrevious, selectCanZoomIn, selectCanZoomOut, selectZoomPercentage, selectPDFUrl, formatFileSize, formatVersionLabel, getDocumentTypeLabel, getDocumentTypeIcon

### frontend/src/stores/pipeline.ts
- Size: 9097 bytes
- Lines: 269
- Exports: usePipelineStore

### frontend/src/stores/production.ts
- Size: 3159 bytes
- Lines: 108
- Exports: useProductionStore

### frontend/src/stores/products.ts
- Size: 2573 bytes
- Lines: 89
- Exports: useProductStore

### frontend/src/stores/project-management-store.ts
- Size: 25284 bytes
- Lines: 747
- Exports: useProjectManagementStore

### frontend/src/stores/quality.ts
- Size: 5848 bytes
- Lines: 209
- Exports: useQualityStore

### frontend/src/stores/quick-actions-store.ts
- Size: 23616 bytes
- Lines: 863
- Exports: DEFAULT_ACTIONS, ENTITY_ACTION_MAP, getActionsForEntity, filterByVisibility, getPrimaryActions, getSecondaryActions, getOverflowActions, hasPermission, filterByPermissions, getActionById, getActionByType, formatEntityType, generateExecutionId, useQuickActionsStore, selectCurrentContext, selectIsBarVisible, selectIsExpanded, selectConfirmation, selectCurrentExecution, selectExecutions

### frontend/src/stores/quote.ts
- Size: 7266 bytes
- Lines: 237
- Exports: useQuoteStore

### frontend/src/stores/quotes.ts
- Size: 8862 bytes
- Lines: 272
- Exports: useQuoteStore

### frontend/src/stores/supply-chain.ts
- Size: 1411 bytes
- Lines: 53
- Exports: useSupplyChainStore

### frontend/src/stores/sync-store.ts
- Size: 6056 bytes
- Lines: 218
- Exports: useSyncStore

### frontend/src/stores/tasks.ts
- Size: 2724 bytes
- Lines: 93
- Exports: useTasksStore

### frontend/src/stores/today.ts
- Size: 744 bytes
- Lines: 28
- Exports: useTodayStore

### frontend/src/stores/training.ts
- Size: 3782 bytes
- Lines: 138
- Exports: useTrainingStore

### frontend/src/stores/ui-store.ts
- Size: 5835 bytes
- Lines: 193
- Exports: useUIStore

### frontend/src/types/index.ts
- Size: 22122 bytes
- Lines: 1023
- Exports: None

### frontend/tailwind.config.ts
- Size: 5306 bytes
- Lines: 154
- Exports: None

### frontend/test_results.json
- Size: 2332482 bytes
- Lines: 2
- Top-level keys: numFailedTestSuites, numFailedTests, numPassedTestSuites, numPassedTests, numPendingTestSuites, numPendingTests, numRuntimeErrorTestSuites, numTodoTests, numTotalTestSuites, numTotalTests, openHandles, snapshot, startTime, success, testResults, wasInterrupted

### frontend/tsconfig.json
- Size: 1000 bytes
- Lines: 36
- Top-level keys: compilerOptions, include, exclude

### frontend/tsconfig.tsbuildinfo
- Size: 198498 bytes
- Lines: 1
- Snippet: {"program":{"fileNames":["./node_modules/typescript/lib/lib.es5.d.ts","./node_modules/typescript/lib/lib.es2015.d.ts","./node_modules/typescript/lib/lib.es2016.d.ts","./node_modules/typescript/lib/lib

### k8s/helm/sensei/Chart.yaml
- Size: 651 bytes
- Lines: 29
- Top-level keys (heuristic): apiVersion, name, description, type, version, appVersion, keywords, maintainers, home, sources, dependencies

### k8s/helm/sensei/templates/NOTES.txt
- Size: 3408 bytes
- Lines: 61
- Snippet: **************************************************

### k8s/helm/sensei/templates/_helpers.tpl
- Size: 3032 bytes
- Lines: 120
- Snippet: {{/*

### k8s/helm/sensei/templates/configmap.yaml
- Size: 1028 bytes
- Lines: 21
- Top-level keys (heuristic): apiVersion, kind, metadata, data

### k8s/helm/sensei/templates/deployment-backend.yaml
- Size: 2650 bytes
- Lines: 76
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/deployment-frontend.yaml
- Size: 2182 bytes
- Lines: 62
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/deployment-worker.yaml
- Size: 2036 bytes
- Lines: 59
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/external-secret.yaml
- Size: 775 bytes
- Lines: 24
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/hpa.yaml
- Size: 1923 bytes
- Lines: 60
- Top-level keys (heuristic): apiVersion, kind, metadata, spec, apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/ingress.yaml
- Size: 1166 bytes
- Lines: 42
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/networkpolicy.yaml
- Size: 2368 bytes
- Lines: 87
- Top-level keys (heuristic): apiVersion, kind, metadata, spec, apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/pdb.yaml
- Size: 797 bytes
- Lines: 28
- Top-level keys (heuristic): apiVersion, kind, metadata, spec, apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/pvc.yaml
- Size: 617 bytes
- Lines: 22
- Top-level keys (heuristic): apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/secret.yaml
- Size: 782 bytes
- Lines: 20
- Top-level keys (heuristic): apiVersion, kind, metadata, type, stringData

### k8s/helm/sensei/templates/service.yaml
- Size: 937 bytes
- Lines: 36
- Top-level keys (heuristic): apiVersion, kind, metadata, spec, apiVersion, kind, metadata, spec

### k8s/helm/sensei/templates/serviceaccount.yaml
- Size: 318 bytes
- Lines: 13
- Top-level keys (heuristic): apiVersion, kind, metadata

### k8s/helm/sensei/values-hetzner.yaml
- Size: 6788 bytes
- Lines: 285
- Top-level keys (heuristic): replicaCount, image, service, ingress, config, resources, autoscaling, healthChecks, postgresql, redis, podDisruptionBudget, persistence, nodeSelector, tolerations, affinity, global, monitoring, logging

### k8s/helm/sensei/values.yaml
- Size: 6979 bytes
- Lines: 358
- Top-level keys (heuristic): global, replicaCount, image, service, ingress, config, externalSecrets, resources, autoscaling, healthChecks, postgresql, redis, minio, worker, persistence, securityContext, podSecurityContext, networkPolicy, serviceAccount, podDisruptionBudget

### move_services.sh
- Size: 8076 bytes
- Lines: 170
- Commands: mv backend/src/sensei/services/ai_reasoning.py \ | backend/src/sensei/services/ai_content_drafting.py \ | backend/src/sensei/services/ai_ctq_summarization.py \ | backend/src/sensei/services/ai_email_drafting.py \ | backend/src/sensei/services/ai_learning_recommendations.py \ | backend/src/sensei/services/ai_qualification_advisory.py \ | backend/src/sensei/services/reasoning_engine.py \ | backend/src/sensei/services/enhanced_ml_pipeline.py \

### package-lock.json
- Size: 7252 bytes
- Lines: 196
- Top-level keys: name, lockfileVersion, requires, packages

### package.json
- Size: 166 bytes
- Lines: 9
- Top-level keys: dependencies

### refactor_imports.py
- Size: 6374 bytes
- Lines: 154
- Classes: None
- Functions: refactor_file

### regroup_frontend.sh
- Size: 895 bytes
- Lines: 35
- Commands: set -e | BASE="frontend/src/app/(dashboard)" | mv "$BASE/admin" "$BASE/(admin)/" | mv "$BASE/settings" "$BASE/(admin)/" | mv "$BASE/analytics" "$BASE/(admin)/" | mv "$BASE/executive" "$BASE/(admin)/" | mv "$BASE/production" "$BASE/(shop-floor)/" | mv "$BASE/andon" "$BASE/(shop-floor)/"

### reproduce_jit_errors.py
- Size: 2138 bytes
- Lines: 52
- Classes: None
- Functions: None

### system_training_report.json
- Size: 2118 bytes
- Lines: 90
- Top-level keys: total_domains, processed_urls, failed_urls, ingested_chunks, details, status, timestamp
