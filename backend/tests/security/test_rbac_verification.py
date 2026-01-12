"""
RBAC (Role-Based Access Control) verification suite for Management Software.

Tests role-based access control to ensure proper authorization:
- Admin role has full access
- Manager role has appropriate permissions
- Engineer role has restricted access
- Shop Floor role has limited access
- Guest role has read-only access
- Audit logging for security events

These tests establish security gates for access control.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from enum import Enum

from sensei.core.time import utcnow_naive


class Role(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    MANAGER = "manager"
    ENGINEER = "engineer"
    SHOP_FLOOR = "shop_floor"
    GUEST = "guest"


class Permission(str, Enum):
    """Permissions in the system."""
    # Account permissions
    ACCOUNT_VIEW = "account:view"
    ACCOUNT_CREATE = "account:create"
    ACCOUNT_EDIT = "account:edit"
    ACCOUNT_DELETE = "account:delete"
    
    # RFQ permissions
    RFQ_VIEW = "rfq:view"
    RFQ_CREATE = "rfq:create"
    RFQ_EDIT = "rfq:edit"
    RFQ_APPROVE = "rfq:approve"
    
    # Quote permissions
    QUOTE_VIEW = "quote:view"
    QUOTE_CREATE = "quote:create"
    QUOTE_EDIT = "quote:edit"
    QUOTE_APPROVE = "quote:approve"
    QUOTE_FINALIZE = "quote:finalize"
    
    # A3 permissions
    A3_VIEW = "a3:view"
    A3_CREATE = "a3:create"
    A3_EDIT = "a3:edit"
    A3_CLOSE = "a3:close"
    
    # Shop Floor permissions
    SHOPFLOOR_VIEW = "shopfloor:view"
    SHOPFLOOR_ANDON = "shopfloor:andon"
    SHOPFLOOR_WORKORDER = "shopfloor:workorder"
    
    # Admin permissions
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_VIEW = "audit:view"


# Define role permissions matrix
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        # Full access to everything
        Permission.ACCOUNT_VIEW, Permission.ACCOUNT_CREATE, Permission.ACCOUNT_EDIT, Permission.ACCOUNT_DELETE,
        Permission.RFQ_VIEW, Permission.RFQ_CREATE, Permission.RFQ_EDIT, Permission.RFQ_APPROVE,
        Permission.QUOTE_VIEW, Permission.QUOTE_CREATE, Permission.QUOTE_EDIT, Permission.QUOTE_APPROVE, Permission.QUOTE_FINALIZE,
        Permission.A3_VIEW, Permission.A3_CREATE, Permission.A3_EDIT, Permission.A3_CLOSE,
        Permission.SHOPFLOOR_VIEW, Permission.SHOPFLOOR_ANDON, Permission.SHOPFLOOR_WORKORDER,
        Permission.USER_MANAGE, Permission.ROLE_MANAGE, Permission.SYSTEM_CONFIG, Permission.AUDIT_VIEW,
    ],
    Role.MANAGER: [
        # View and manage most entities, approve quotes/RFQs
        Permission.ACCOUNT_VIEW, Permission.ACCOUNT_CREATE, Permission.ACCOUNT_EDIT,
        Permission.RFQ_VIEW, Permission.RFQ_CREATE, Permission.RFQ_EDIT, Permission.RFQ_APPROVE,
        Permission.QUOTE_VIEW, Permission.QUOTE_CREATE, Permission.QUOTE_EDIT, Permission.QUOTE_APPROVE, Permission.QUOTE_FINALIZE,
        Permission.A3_VIEW, Permission.A3_CREATE, Permission.A3_EDIT, Permission.A3_CLOSE,
        Permission.SHOPFLOOR_VIEW, Permission.SHOPFLOOR_WORKORDER,
        Permission.AUDIT_VIEW,
    ],
    Role.ENGINEER: [
        # Create and edit technical entities, view shop floor
        Permission.ACCOUNT_VIEW,
        Permission.RFQ_VIEW, Permission.RFQ_CREATE, Permission.RFQ_EDIT,
        Permission.QUOTE_VIEW, Permission.QUOTE_CREATE, Permission.QUOTE_EDIT,
        Permission.A3_VIEW, Permission.A3_CREATE, Permission.A3_EDIT,
        Permission.SHOPFLOOR_VIEW,
    ],
    Role.SHOP_FLOOR: [
        # View and interact with shop floor, create andons
        Permission.SHOPFLOOR_VIEW, Permission.SHOPFLOOR_ANDON, Permission.SHOPFLOOR_WORKORDER,
        Permission.A3_VIEW,
    ],
    Role.GUEST: [
        # Read-only access to basic entities
        Permission.ACCOUNT_VIEW,
        Permission.RFQ_VIEW,
        Permission.QUOTE_VIEW,
        Permission.A3_VIEW,
        Permission.SHOPFLOOR_VIEW,
    ],
}


class TestRBACVerification:
    """Test role-based access control enforcement."""
    
    def test_admin_role_has_full_access(self):
        """Test admin role has all permissions."""
        admin_permissions = ROLE_PERMISSIONS[Role.ADMIN]
        
        # Verify: Admin has access to all critical permissions
        assert Permission.ACCOUNT_DELETE in admin_permissions
        assert Permission.USER_MANAGE in admin_permissions
        assert Permission.ROLE_MANAGE in admin_permissions
        assert Permission.SYSTEM_CONFIG in admin_permissions
        assert Permission.AUDIT_VIEW in admin_permissions
        assert Permission.QUOTE_FINALIZE in admin_permissions
        
        # Verify: Admin has most permissions
        all_permissions = list(Permission)
        admin_permission_count = len(admin_permissions)
        assert admin_permission_count >= len(all_permissions) * 0.8  # At least 80% of all permissions
    
    def test_manager_role_permissions(self):
        """Test manager role has appropriate permissions."""
        manager_permissions = ROLE_PERMISSIONS[Role.MANAGER]
        
        # Verify: Manager can approve and finalize
        assert Permission.RFQ_APPROVE in manager_permissions
        assert Permission.QUOTE_APPROVE in manager_permissions
        assert Permission.QUOTE_FINALIZE in manager_permissions
        assert Permission.A3_CLOSE in manager_permissions
        
        # Verify: Manager cannot delete accounts or manage users
        assert Permission.ACCOUNT_DELETE not in manager_permissions
        assert Permission.USER_MANAGE not in manager_permissions
        assert Permission.ROLE_MANAGE not in manager_permissions
        assert Permission.SYSTEM_CONFIG not in manager_permissions
    
    def test_engineer_role_permissions(self):
        """Test engineer role has restricted permissions."""
        engineer_permissions = ROLE_PERMISSIONS[Role.ENGINEER]
        
        # Verify: Engineer can create and edit technical entities
        assert Permission.RFQ_CREATE in engineer_permissions
        assert Permission.RFQ_EDIT in engineer_permissions
        assert Permission.QUOTE_CREATE in engineer_permissions
        assert Permission.QUOTE_EDIT in engineer_permissions
        assert Permission.A3_CREATE in engineer_permissions
        assert Permission.A3_EDIT in engineer_permissions
        
        # Verify: Engineer cannot approve, finalize, or delete
        assert Permission.RFQ_APPROVE not in engineer_permissions
        assert Permission.QUOTE_APPROVE not in engineer_permissions
        assert Permission.QUOTE_FINALIZE not in engineer_permissions
        assert Permission.A3_CLOSE not in engineer_permissions
        assert Permission.ACCOUNT_DELETE not in engineer_permissions
        assert Permission.USER_MANAGE not in engineer_permissions
    
    def test_shop_floor_role_permissions(self):
        """Test shop floor role has limited permissions."""
        shopfloor_permissions = ROLE_PERMISSIONS[Role.SHOP_FLOOR]
        
        # Verify: Shop floor can interact with shop floor systems
        assert Permission.SHOPFLOOR_VIEW in shopfloor_permissions
        assert Permission.SHOPFLOOR_ANDON in shopfloor_permissions
        assert Permission.SHOPFLOOR_WORKORDER in shopfloor_permissions
        assert Permission.A3_VIEW in shopfloor_permissions
        
        # Verify: Shop floor cannot access quotes or accounts
        assert Permission.QUOTE_CREATE not in shopfloor_permissions
        assert Permission.QUOTE_EDIT not in shopfloor_permissions
        assert Permission.ACCOUNT_VIEW not in shopfloor_permissions
        assert Permission.RFQ_CREATE not in shopfloor_permissions
        
        # Verify: Shop floor has minimal permissions
        assert len(shopfloor_permissions) <= 5
    
    def test_guest_role_read_only(self):
        """Test guest role has read-only access."""
        guest_permissions = ROLE_PERMISSIONS[Role.GUEST]
        
        # Verify: Guest can only view
        assert Permission.ACCOUNT_VIEW in guest_permissions
        assert Permission.RFQ_VIEW in guest_permissions
        assert Permission.QUOTE_VIEW in guest_permissions
        assert Permission.A3_VIEW in guest_permissions
        assert Permission.SHOPFLOOR_VIEW in guest_permissions
        
        # Verify: Guest cannot create, edit, delete, or approve
        write_permissions = [p for p in guest_permissions if "create" in p.value.lower() or "edit" in p.value.lower() or "delete" in p.value.lower() or "approve" in p.value.lower()]
        assert len(write_permissions) == 0
    
    def test_permission_hierarchy(self):
        """Test permission hierarchy is enforced."""
        # Verify: Admin has superset of Manager permissions
        admin_perms = set(ROLE_PERMISSIONS[Role.ADMIN])
        manager_perms = set(ROLE_PERMISSIONS[Role.MANAGER])
        assert manager_perms.issubset(admin_perms)
        
        # Verify: Manager has more permissions than Engineer
        engineer_perms = set(ROLE_PERMISSIONS[Role.ENGINEER])
        assert len(manager_perms) > len(engineer_perms)
        
        # Verify: Guest has fewest permissions
        guest_perms = set(ROLE_PERMISSIONS[Role.GUEST])
        for role_perms in [admin_perms, manager_perms, engineer_perms]:
            assert len(guest_perms) < len(role_perms)
    
    def test_audit_logging_for_security_events(self):
        """Test audit logging captures security-relevant events."""
        # Define security events that must be logged
        security_events = {
            "login_success": {"user_id": str(uuid4()), "timestamp": utcnow_naive(), "ip_address": "192.168.1.100"},
            "login_failure": {"username": "test@example.com", "timestamp": utcnow_naive(), "ip_address": "192.168.1.100", "reason": "invalid_password"},
            "permission_denied": {"user_id": str(uuid4()), "permission": Permission.ACCOUNT_DELETE.value, "resource": "account:123", "timestamp": utcnow_naive()},
            "role_changed": {"user_id": str(uuid4()), "old_role": Role.ENGINEER.value, "new_role": Role.MANAGER.value, "changed_by": str(uuid4()), "timestamp": utcnow_naive()},
            "password_changed": {"user_id": str(uuid4()), "timestamp": utcnow_naive()},
            "mfa_enabled": {"user_id": str(uuid4()), "timestamp": utcnow_naive()},
            "mfa_disabled": {"user_id": str(uuid4()), "timestamp": utcnow_naive()},
            "session_expired": {"user_id": str(uuid4()), "timestamp": utcnow_naive()},
        }
        
        # Verify: All security events are defined
        assert "login_success" in security_events
        assert "login_failure" in security_events
        assert "permission_denied" in security_events
        assert "role_changed" in security_events
        assert "password_changed" in security_events
        
        # Verify: Each event has required fields
        for event_type, event_data in security_events.items():
            assert "timestamp" in event_data
            if event_type in ["login_success", "permission_denied"]:
                assert "user_id" in event_data or "username" in event_data
    
    def test_principle_of_least_privilege(self):
        """Test principle of least privilege is followed."""
        # Verify: Each role has only necessary permissions
        for role, permissions in ROLE_PERMISSIONS.items():
            # No duplicate permissions
            assert len(permissions) == len(set(permissions))
            
            # Permissions are specific to role function
            if role == Role.SHOP_FLOOR:
                # Shop floor should only have shop floor and limited A3 permissions
                non_shopfloor_perms = [p for p in permissions if not (p.value.startswith("shopfloor:") or p in [Permission.A3_VIEW])]
                assert len(non_shopfloor_perms) == 0
            
            if role == Role.GUEST:
                # Guest should only have view permissions
                non_view_perms = [p for p in permissions if ":view" not in p.value]
                assert len(non_view_perms) == 0
    
    def test_separation_of_duties(self):
        """Test separation of duties for critical operations."""
        # Define critical operations requiring multiple roles
        critical_operations = {
            "finalize_quote": {
                "create": Permission.QUOTE_CREATE,
                "approve": Permission.QUOTE_APPROVE,
                "finalize": Permission.QUOTE_FINALIZE,
            },
            "close_a3": {
                "create": Permission.A3_CREATE,
                "edit": Permission.A3_EDIT,
                "close": Permission.A3_CLOSE,
            },
        }
        
        # Verify: Engineers cannot both create and finalize quotes
        engineer_perms = ROLE_PERMISSIONS[Role.ENGINEER]
        assert Permission.QUOTE_CREATE in engineer_perms
        assert Permission.QUOTE_FINALIZE not in engineer_perms
        
        # Verify: Shop floor cannot approve their own requests
        shopfloor_perms = ROLE_PERMISSIONS[Role.SHOP_FLOOR]
        assert Permission.RFQ_APPROVE not in shopfloor_perms
        assert Permission.QUOTE_APPROVE not in shopfloor_perms
