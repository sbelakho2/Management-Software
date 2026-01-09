"""
Tests for RBAC Security Audit Service.

Tests comprehensive verification of Role-Based Access Control (RBAC)
and Audit Log integrity for security compliance.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from sensei.services.rbac_security_audit import (
    RBACSecurityAuditService,
    AuditSeverity,
    AuditCategory,
    ComplianceStatus,
    AuditFinding,
    RoleConfig,
    PermissionConfig,
    UserRoleAssignment,
    AuditLogEntry,
    AccessPattern,
    ComplianceReport,
    get_rbac_security_audit_service,
    reset_rbac_security_audit_service,
)


@pytest.fixture
def service():
    """Create a fresh service for each test."""
    reset_rbac_security_audit_service()
    return get_rbac_security_audit_service()


@pytest.fixture
def sample_role_id():
    """Generate a sample role ID."""
    return uuid4()


@pytest.fixture
def sample_permission_id():
    """Generate a sample permission ID."""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return uuid4()


# ===== Singleton Tests =====


class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_returns_same_instance(self):
        """Test that get always returns the same instance."""
        reset_rbac_security_audit_service()
        service1 = get_rbac_security_audit_service()
        service2 = get_rbac_security_audit_service()
        assert service1 is service2
    
    def test_reset_creates_new_instance(self):
        """Test that reset clears the singleton."""
        service1 = get_rbac_security_audit_service()
        service1.register_role(uuid4(), "test", "Test", permission_count=5)
        
        reset_rbac_security_audit_service()
        service2 = get_rbac_security_audit_service()
        
        assert len(service2.get_all_roles()) == 0


# ===== Role Management Tests =====


class TestRoleManagement:
    """Tests for role registration and retrieval."""
    
    def test_register_role(self, service, sample_role_id):
        """Test registering a role."""
        role = service.register_role(
            role_id=sample_role_id,
            name="admin",
            display_name="Administrator",
            role_type="admin",
            is_system=True,
            is_active=True,
            hierarchy_level=10,
            permission_count=25,
            user_count=2,
        )
        
        assert isinstance(role, RoleConfig)
        assert role.id == sample_role_id
        assert role.name == "admin"
        assert role.is_system is True
        assert role.hierarchy_level == 10
    
    def test_get_role(self, service, sample_role_id):
        """Test getting a registered role."""
        service.register_role(sample_role_id, "test", "Test Role")
        
        role = service.get_role(sample_role_id)
        
        assert role is not None
        assert role.name == "test"
    
    def test_get_role_not_found(self, service):
        """Test getting a non-existent role."""
        result = service.get_role(uuid4())
        assert result is None
    
    def test_get_all_roles(self, service):
        """Test getting all registered roles."""
        service.register_role(uuid4(), "role1", "Role 1")
        service.register_role(uuid4(), "role2", "Role 2")
        service.register_role(uuid4(), "role3", "Role 3")
        
        roles = service.get_all_roles()
        
        assert len(roles) == 3
    
    def test_role_to_dict(self, service, sample_role_id):
        """Test role serialization."""
        role = service.register_role(
            sample_role_id, "test", "Test Role",
            role_type="admin",
            hierarchy_level=15,
        )
        
        data = role.to_dict()
        
        assert data["id"] == str(sample_role_id)
        assert data["name"] == "test"
        assert data["hierarchy_level"] == 15


# ===== Permission Management Tests =====


class TestPermissionManagement:
    """Tests for permission registration and retrieval."""
    
    def test_register_permission(self, service, sample_permission_id):
        """Test registering a permission."""
        perm = service.register_permission(
            permission_id=sample_permission_id,
            name="quotes:create",
            display_name="Create Quotes",
            resource="quotes",
            action="create",
            is_system=True,
            role_count=3,
        )
        
        assert isinstance(perm, PermissionConfig)
        assert perm.id == sample_permission_id
        assert perm.resource == "quotes"
        assert perm.action == "create"
    
    def test_get_permission(self, service, sample_permission_id):
        """Test getting a registered permission."""
        service.register_permission(
            sample_permission_id, "test:read", "Test Read",
            resource="test", action="read",
        )
        
        perm = service.get_permission(sample_permission_id)
        
        assert perm is not None
        assert perm.name == "test:read"
    
    def test_get_all_permissions(self, service):
        """Test getting all registered permissions."""
        for i in range(5):
            service.register_permission(
                uuid4(), f"perm{i}", f"Perm {i}",
                resource=f"res{i}", action="read",
            )
        
        perms = service.get_all_permissions()
        
        assert len(perms) == 5
    
    def test_permission_to_dict(self, service, sample_permission_id):
        """Test permission serialization."""
        perm = service.register_permission(
            sample_permission_id, "users:delete", "Delete Users",
            resource="users", action="delete", is_system=True,
        )
        
        data = perm.to_dict()
        
        assert data["resource"] == "users"
        assert data["action"] == "delete"
        assert data["is_system"] is True


# ===== User-Role Assignment Tests =====


class TestUserRoleAssignment:
    """Tests for user-role assignment registration."""
    
    def test_register_user_role(self, service, sample_user_id, sample_role_id):
        """Test registering a user-role assignment."""
        now = datetime.now(timezone.utc)
        
        assignment = service.register_user_role(
            user_id=sample_user_id,
            user_email="user@example.com",
            role_id=sample_role_id,
            role_name="admin",
            assigned_at=now,
            assigned_by_id=uuid4(),
            is_active=True,
        )
        
        assert isinstance(assignment, UserRoleAssignment)
        assert assignment.user_id == sample_user_id
        assert assignment.role_name == "admin"
        assert assignment.is_expired is False
    
    def test_register_expired_user_role(self, service, sample_user_id, sample_role_id):
        """Test registering an expired user-role assignment."""
        past = datetime.now(timezone.utc) - timedelta(days=30)
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        
        assignment = service.register_user_role(
            user_id=sample_user_id,
            user_email="user@example.com",
            role_id=sample_role_id,
            role_name="temp_role",
            assigned_at=past,
            expires_at=expired,
            is_active=True,
        )
        
        assert assignment.is_expired is True
    
    def test_get_user_roles(self, service, sample_user_id):
        """Test getting roles for a user."""
        service.register_user_role(
            sample_user_id, "user@test.com", uuid4(), "role1",
            datetime.now(timezone.utc),
        )
        service.register_user_role(
            sample_user_id, "user@test.com", uuid4(), "role2",
            datetime.now(timezone.utc),
        )
        
        roles = service.get_user_roles(sample_user_id)
        
        assert len(roles) == 2
    
    def test_get_all_user_roles(self, service):
        """Test getting all user-role assignments."""
        for i in range(3):
            service.register_user_role(
                uuid4(), f"user{i}@test.com", uuid4(), f"role{i}",
                datetime.now(timezone.utc),
            )
        
        assignments = service.get_all_user_roles()
        
        assert len(assignments) == 3
    
    def test_user_role_to_dict(self, service, sample_user_id, sample_role_id):
        """Test user-role serialization."""
        now = datetime.now(timezone.utc)
        
        assignment = service.register_user_role(
            sample_user_id, "user@test.com", sample_role_id, "admin", now,
        )
        
        data = assignment.to_dict()
        
        assert data["user_id"] == str(sample_user_id)
        assert data["role_name"] == "admin"
        assert data["is_active"] is True


# ===== Audit Log Tests =====


class TestAuditLogManagement:
    """Tests for audit log registration and retrieval."""
    
    def test_register_audit_log(self, service, sample_user_id):
        """Test registering an audit log entry."""
        entity_id = uuid4()
        now = datetime.now(timezone.utc)
        
        entry = service.register_audit_log(
            log_id=uuid4(),
            entity_type="quotes",
            entity_id=entity_id,
            action="create",
            created_at=now,
            user_id=sample_user_id,
            user_email="user@test.com",
            ip_address="192.168.1.1",
            has_new_values=True,
        )
        
        assert isinstance(entry, AuditLogEntry)
        assert entry.entity_type == "quotes"
        assert entry.action == "create"
    
    def test_get_audit_logs_by_entity_type(self, service):
        """Test filtering audit logs by entity type."""
        now = datetime.now(timezone.utc)
        
        service.register_audit_log(uuid4(), "quotes", uuid4(), "create", now)
        service.register_audit_log(uuid4(), "users", uuid4(), "update", now)
        service.register_audit_log(uuid4(), "quotes", uuid4(), "update", now)
        
        quote_logs = service.get_audit_logs(entity_type="quotes")
        
        assert len(quote_logs) == 2
    
    def test_get_audit_logs_by_action(self, service):
        """Test filtering audit logs by action."""
        now = datetime.now(timezone.utc)
        
        service.register_audit_log(uuid4(), "quotes", uuid4(), "create", now)
        service.register_audit_log(uuid4(), "users", uuid4(), "update", now)
        service.register_audit_log(uuid4(), "quotes", uuid4(), "delete", now)
        
        create_logs = service.get_audit_logs(action="create")
        
        assert len(create_logs) == 1
    
    def test_get_audit_logs_by_date_range(self, service):
        """Test filtering audit logs by date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        service.register_audit_log(uuid4(), "quotes", uuid4(), "create", last_week)
        service.register_audit_log(uuid4(), "quotes", uuid4(), "update", yesterday)
        service.register_audit_log(uuid4(), "quotes", uuid4(), "delete", now)
        
        recent_logs = service.get_audit_logs(start_date=yesterday - timedelta(hours=1))
        
        assert len(recent_logs) == 2
    
    def test_audit_log_to_dict(self, service, sample_user_id):
        """Test audit log serialization."""
        entity_id = uuid4()
        now = datetime.now(timezone.utc)
        
        entry = service.register_audit_log(
            uuid4(), "users", entity_id, "update", now,
            user_id=sample_user_id,
            has_old_values=True,
            has_changed_fields=True,
        )
        
        data = entry.to_dict()
        
        assert data["entity_type"] == "users"
        assert data["has_old_values"] is True


# ===== Role Configuration Verification Tests =====


class TestRoleConfigurationVerification:
    """Tests for role configuration verification."""
    
    def test_detect_role_without_permissions(self, service):
        """Test detecting roles without permissions."""
        service.register_role(uuid4(), "empty_role", "Empty Role", is_active=True, permission_count=0)
        
        findings = service.verify_role_configuration()
        
        assert len(findings) == 1
        assert findings[0].category == AuditCategory.RBAC_CONFIG
        assert "without permissions" in findings[0].title.lower()
    
    def test_detect_high_privilege_role_many_users(self, service):
        """Test detecting high-privilege roles with many users."""
        service.register_role(
            uuid4(), "admin", "Admin",
            hierarchy_level=10,  # Very high privilege
            user_count=10,  # Many users
            permission_count=20,
        )
        
        findings = service.verify_role_configuration()
        
        # Should find high-privilege role with many users
        high_priv = [f for f in findings if f.category == AuditCategory.PRIVILEGE_ESCALATION]
        assert len(high_priv) == 1
        assert "many users" in high_priv[0].title.lower()
    
    def test_no_findings_for_valid_config(self, service):
        """Test that valid configuration produces no role findings."""
        service.register_role(
            uuid4(), "normal_role", "Normal Role",
            hierarchy_level=50,
            user_count=3,
            permission_count=10,
            role_type="ops",
        )
        
        findings = service.verify_role_configuration()
        
        # No significant findings
        assert len([f for f in findings if f.severity in [AuditSeverity.CRITICAL, AuditSeverity.HIGH]]) == 0


# ===== Permission Configuration Verification Tests =====


class TestPermissionConfigurationVerification:
    """Tests for permission configuration verification."""
    
    def test_detect_unused_permissions(self, service):
        """Test detecting unused permissions."""
        service.register_permission(
            uuid4(), "unused:perm", "Unused Perm",
            resource="unused", action="perm", role_count=0,
        )
        
        findings = service.verify_permission_configuration()
        
        unused = [f for f in findings if "unused" in f.title.lower()]
        assert len(unused) == 1
    
    def test_detect_sensitive_permission_widely_assigned(self, service):
        """Test detecting sensitive permissions with wide assignment."""
        service.register_permission(
            uuid4(), "users:delete", "Delete Users",
            resource="users", action="delete", role_count=8,
        )
        
        findings = service.verify_permission_configuration()
        
        sensitive = [f for f in findings if "sensitive" in f.title.lower()]
        assert len(sensitive) == 1


# ===== User Assignment Verification Tests =====


class TestUserAssignmentVerification:
    """Tests for user-role assignment verification."""
    
    def test_detect_expired_active_assignment(self, service):
        """Test detecting expired but active assignments."""
        past = datetime.now(timezone.utc) - timedelta(days=30)
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        
        service.register_user_role(
            uuid4(), "user@test.com", uuid4(), "temp_role", past,
            expires_at=expired, is_active=True,
        )
        
        findings = service.verify_user_assignments()
        
        expired_findings = [f for f in findings if "expired" in f.title.lower()]
        assert len(expired_findings) == 1
        assert expired_findings[0].severity == AuditSeverity.HIGH
    
    def test_detect_self_assigned_role(self, service):
        """Test detecting self-assigned roles."""
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        
        service.register_user_role(
            user_id, "self@test.com", uuid4(), "admin", now,
            assigned_by_id=user_id,  # Self-assigned
        )
        
        findings = service.verify_user_assignments()
        
        self_assigned = [f for f in findings if "self-assigned" in f.title.lower()]
        assert len(self_assigned) == 1
        assert self_assigned[0].severity == AuditSeverity.CRITICAL
    
    def test_detect_user_with_multiple_high_privilege_roles(self, service):
        """Test detecting users with multiple high-privilege roles."""
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        
        # Register high-privilege roles
        admin_id = uuid4()
        exec_id = uuid4()
        service.register_role(admin_id, "admin", "Admin", hierarchy_level=10, permission_count=20)
        service.register_role(exec_id, "exec", "Executive", hierarchy_level=15, permission_count=15)
        
        # Assign both to same user
        service.register_user_role(user_id, "user@test.com", admin_id, "admin", now)
        service.register_user_role(user_id, "user@test.com", exec_id, "exec", now)
        
        findings = service.verify_user_assignments()
        
        multi_priv = [f for f in findings if "multiple high-privilege" in f.title.lower()]
        assert len(multi_priv) == 1


# ===== Audit Log Integrity Verification Tests =====


class TestAuditLogIntegrityVerification:
    """Tests for audit log integrity verification."""
    
    def test_detect_anonymous_logs(self, service):
        """Test detecting audit logs without user attribution."""
        now = datetime.now(timezone.utc)
        
        # Anonymous log (not login/logout)
        service.register_audit_log(
            uuid4(), "quotes", uuid4(), "create", now,
            user_id=None, user_email=None,
        )
        
        findings = service.verify_audit_log_integrity()
        
        anon = [f for f in findings if "without user attribution" in f.title.lower()]
        assert len(anon) == 1
    
    def test_detect_updates_without_change_details(self, service):
        """Test detecting update logs without change details."""
        now = datetime.now(timezone.utc)
        user_id = uuid4()
        
        service.register_audit_log(
            uuid4(), "quotes", uuid4(), "update", now,
            user_id=user_id,
            has_old_values=False, has_changed_fields=False,
        )
        
        findings = service.verify_audit_log_integrity()
        
        no_details = [f for f in findings if "without change details" in f.title.lower()]
        assert len(no_details) == 1
    
    def test_detect_missing_sensitive_resources(self, service):
        """Test detecting sensitive resources not in audit logs."""
        now = datetime.now(timezone.utc)
        
        # Only log to non-sensitive resource
        service.register_audit_log(
            uuid4(), "widgets", uuid4(), "create", now,
        )
        
        findings = service.verify_audit_log_integrity()
        
        missing = [f for f in findings if "sensitive resources" in f.title.lower()]
        assert len(missing) == 1
    
    def test_detect_audit_log_gap(self, service):
        """Test detecting gaps in audit log timeline."""
        old = datetime.now(timezone.utc) - timedelta(days=5)
        recent = datetime.now(timezone.utc)
        
        service.register_audit_log(uuid4(), "users", uuid4(), "create", old)
        service.register_audit_log(uuid4(), "users", uuid4(), "update", recent)
        
        findings = service.verify_audit_log_integrity()
        
        gaps = [f for f in findings if "gap" in f.title.lower()]
        assert len(gaps) == 1
    
    def test_login_logs_allowed_anonymous(self, service):
        """Test that login/logout logs can be anonymous."""
        now = datetime.now(timezone.utc)
        
        service.register_audit_log(
            uuid4(), "session", uuid4(), "login", now,
            user_id=None,  # Anonymous but allowed for login
        )
        
        findings = service.verify_audit_log_integrity()
        
        # Should not find anonymous warning for login
        anon = [f for f in findings if "without user attribution" in f.title.lower()]
        assert len(anon) == 0


# ===== Access Pattern Analysis Tests =====


class TestAccessPatternAnalysis:
    """Tests for access pattern detection and anomaly analysis."""
    
    def test_record_access_pattern(self, service, sample_user_id):
        """Test recording access patterns."""
        now = datetime.now(timezone.utc)
        
        pattern = service.record_access_pattern(
            sample_user_id, "user@test.com", "read", "quotes", now, uuid4(),
        )
        
        assert isinstance(pattern, AccessPattern)
        assert pattern.count == 1
        assert pattern.resource == "quotes"
    
    def test_access_pattern_accumulates(self, service, sample_user_id):
        """Test that access patterns accumulate correctly."""
        now = datetime.now(timezone.utc)
        
        for i in range(10):
            service.record_access_pattern(
                sample_user_id, "user@test.com", "read", "quotes",
                now + timedelta(minutes=i), uuid4(),
            )
        
        patterns = service.get_access_patterns(sample_user_id)
        
        assert len(patterns) == 1
        assert patterns[0].count == 10
    
    def test_detect_unusual_access_pattern(self, service):
        """Test detecting unusual access patterns."""
        now = datetime.now(timezone.utc)
        
        # Create normal baseline
        for i in range(5):
            user_id = uuid4()
            for j in range(5):
                service.record_access_pattern(
                    user_id, f"user{i}@test.com", "read", "quotes", now,
                )
        
        # Create outlier
        heavy_user = uuid4()
        for _ in range(50):
            service.record_access_pattern(
                heavy_user, "heavy@test.com", "read", "quotes", now,
            )
        
        findings = service.detect_access_anomalies()
        
        unusual = [f for f in findings if "unusual" in f.title.lower()]
        assert len(unusual) == 1
    
    def test_detect_off_hours_access(self, service, sample_user_id):
        """Test detecting off-hours access."""
        # 3 AM access
        off_hours = datetime.now(timezone.utc).replace(hour=3)
        
        service.record_access_pattern(
            sample_user_id, "night@test.com", "read", "quotes", off_hours,
        )
        
        findings = service.detect_access_anomalies()
        
        off_hour = [f for f in findings if "off-hours" in f.title.lower()]
        assert len(off_hour) == 1
    
    def test_get_access_patterns_filtered(self, service):
        """Test getting access patterns with filter."""
        user1 = uuid4()
        user2 = uuid4()
        now = datetime.now(timezone.utc)
        
        service.record_access_pattern(user1, "u1@test.com", "read", "quotes", now)
        service.record_access_pattern(user2, "u2@test.com", "read", "quotes", now)
        
        patterns = service.get_access_patterns(user1)
        
        assert len(patterns) == 1
        assert patterns[0].user_id == user1


# ===== Findings Management Tests =====


class TestFindingsManagement:
    """Tests for audit findings management."""
    
    def test_get_all_findings(self, service):
        """Test getting all findings after audit."""
        # Create data that will generate findings
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        service.verify_role_configuration()
        
        findings = service.get_all_findings()
        
        assert len(findings) >= 1
    
    def test_get_findings_by_severity(self, service):
        """Test filtering findings by severity."""
        # Self-assigned role creates CRITICAL finding
        user_id = uuid4()
        service.register_user_role(
            user_id, "self@test.com", uuid4(), "admin",
            datetime.now(timezone.utc), assigned_by_id=user_id,
        )
        service.verify_user_assignments()
        
        critical = service.get_all_findings(severity=AuditSeverity.CRITICAL)
        
        assert len(critical) >= 1
    
    def test_get_findings_by_category(self, service):
        """Test filtering findings by category."""
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        service.verify_role_configuration()
        
        rbac = service.get_all_findings(category=AuditCategory.RBAC_CONFIG)
        
        assert len(rbac) >= 1
    
    def test_resolve_finding(self, service):
        """Test marking a finding as resolved."""
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        service.verify_role_configuration()
        
        findings = service.get_all_findings()
        finding_id = findings[0].id
        
        resolved = service.resolve_finding(finding_id, "admin@test.com")
        
        assert resolved is not None
        assert resolved.resolved is True
        assert resolved.resolved_by == "admin@test.com"
    
    def test_resolve_finding_not_found(self, service):
        """Test resolving a non-existent finding."""
        result = service.resolve_finding("INVALID-ID", "admin@test.com")
        assert result is None
    
    def test_get_unresolved_findings(self, service):
        """Test filtering for unresolved findings only."""
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        service.verify_role_configuration()
        
        findings = service.get_all_findings()
        service.resolve_finding(findings[0].id, "admin@test.com")
        
        unresolved = service.get_all_findings(resolved=False)
        resolved = service.get_all_findings(resolved=True)
        
        assert len(resolved) == 1
        assert len(unresolved) == len(findings) - 1
    
    def test_get_findings_summary(self, service):
        """Test getting findings summary by severity."""
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        service.verify_role_configuration()
        
        summary = service.get_findings_summary()
        
        assert "critical" in summary
        assert "high" in summary
        assert "medium" in summary
        assert isinstance(summary["medium"], int)


# ===== Compliance Report Tests =====


class TestComplianceReport:
    """Tests for compliance report generation."""
    
    def test_run_full_audit_compliant(self, service):
        """Test full audit with compliant configuration."""
        # Set up minimal compliant data
        role_id = uuid4()
        service.register_role(
            role_id, "viewer", "Viewer", role_type="viewer",
            hierarchy_level=100, permission_count=5, user_count=2,
        )
        
        # Add some audit logs for sensitive resources
        now = datetime.now(timezone.utc)
        for resource in ["users", "roles", "permissions", "settings", "quotes", "rfq", "work_orders", "accounts"]:
            service.register_audit_log(
                uuid4(), resource, uuid4(), "create", now,
                user_id=uuid4(), has_new_values=True,
            )
        
        report = service.run_full_audit()
        
        assert isinstance(report, ComplianceReport)
        assert report.total_checks == 5
        assert report.status in [ComplianceStatus.COMPLIANT, ComplianceStatus.PARTIAL]
    
    def test_run_full_audit_non_compliant(self, service):
        """Test full audit with non-compliant configuration."""
        # Create critical issue (self-assigned role)
        user_id = uuid4()
        service.register_user_role(
            user_id, "self@test.com", uuid4(), "admin",
            datetime.now(timezone.utc), assigned_by_id=user_id,
        )
        
        report = service.run_full_audit()
        
        assert report.status == ComplianceStatus.NON_COMPLIANT
        assert report.findings_by_severity["critical"] >= 1
    
    def test_report_contains_summaries(self, service):
        """Test that report contains all summary sections."""
        service.register_role(uuid4(), "test", "Test", permission_count=5)
        service.register_permission(uuid4(), "test:read", "Read", "test", "read")
        
        report = service.run_full_audit()
        
        assert "total" in report.role_summary
        assert "total" in report.permission_summary
        assert "total" in report.user_assignment_summary
        assert "total_entries" in report.audit_log_summary
    
    def test_report_contains_recommendations(self, service):
        """Test that report contains recommendations."""
        # Create high-severity issue
        service.register_role(uuid4(), "empty", "Empty", permission_count=0)
        
        report = service.run_full_audit()
        
        assert len(report.recommendations) >= 1
    
    def test_report_to_dict(self, service):
        """Test report serialization."""
        service.register_role(uuid4(), "test", "Test", permission_count=5)
        
        report = service.run_full_audit()
        data = report.to_dict()
        
        assert "report_id" in data
        assert "status" in data
        assert "findings" in data
        assert "recommendations" in data


# ===== Clear Data Tests =====


class TestClearData:
    """Tests for clearing service data."""
    
    def test_clear_data(self, service):
        """Test clearing all data."""
        service.register_role(uuid4(), "test", "Test")
        service.register_permission(uuid4(), "test:read", "Read", "test", "read")
        service.register_user_role(uuid4(), "user@test.com", uuid4(), "role", datetime.now(timezone.utc))
        service.register_audit_log(uuid4(), "test", uuid4(), "create", datetime.now(timezone.utc))
        
        service.clear_data()
        
        assert len(service.get_all_roles()) == 0
        assert len(service.get_all_permissions()) == 0
        assert len(service.get_all_user_roles()) == 0
        assert len(service.get_audit_logs()) == 0
        assert len(service.get_all_findings()) == 0


# ===== Data Class Serialization Tests =====


class TestDataClassSerialization:
    """Tests for data class serialization."""
    
    def test_audit_finding_to_dict(self):
        """Test AuditFinding serialization."""
        finding = AuditFinding(
            id="FINDING-0001",
            category=AuditCategory.RBAC_CONFIG,
            severity=AuditSeverity.HIGH,
            title="Test Finding",
            description="Test description",
            affected_entity_type="role",
            affected_entity_id="123",
            recommendation="Fix it",
            evidence={"key": "value"},
        )
        
        data = finding.to_dict()
        
        assert data["id"] == "FINDING-0001"
        assert data["category"] == "rbac_configuration"
        assert data["severity"] == "high"
        assert data["evidence"] == {"key": "value"}
    
    def test_access_pattern_to_dict(self, sample_user_id):
        """Test AccessPattern serialization."""
        now = datetime.now(timezone.utc)
        
        pattern = AccessPattern(
            user_id=sample_user_id,
            user_email="user@test.com",
            action="read",
            resource="quotes",
            count=10,
            first_access=now - timedelta(hours=1),
            last_access=now,
            unique_entities=5,
        )
        
        data = pattern.to_dict()
        
        assert data["user_id"] == str(sample_user_id)
        assert data["count"] == 10
        assert data["unique_entities"] == 5
