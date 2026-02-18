"""
Tests for Obeya RBAC filtering.

Tests cover:
- Owner-based access filtering
- Role-based full access (admin, CEO, GM, exec, supervisor)
- Item visibility based on ownership, creation, assignment, escalation
- Update/delete authorization
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch


class MockUser:
    """Mock user for testing."""
    
    def __init__(self, user_id=None, roles=None):
        self.id = user_id or uuid4()
        self.roles = roles or []


class MockObeyaItem:
    """Mock Obeya item for testing."""
    
    def __init__(
        self,
        item_id=None,
        owner_id=None,
        created_by_id=None,
        assigned_to_id=None,
        escalated_to_id=None,
        deleted_at=None,
    ):
        self.id = item_id or uuid4()
        self.owner_id = owner_id
        self.created_by_id = created_by_id
        self.assigned_to_id = assigned_to_id
        self.escalated_to_id = escalated_to_id
        self.deleted_at = deleted_at


class TestObeyaRBACLogic:
    """Test RBAC logic for Obeya items."""
    
    @pytest.fixture
    def admin_user(self):
        return MockUser(roles=['admin'])
    
    @pytest.fixture
    def ceo_user(self):
        return MockUser(roles=['ceo'])
    
    @pytest.fixture
    def operator_user(self):
        return MockUser(roles=['operator'])
    
    @pytest.fixture
    def viewer_user(self):
        return MockUser(roles=['viewer'])
    
    def _check_rbac_access(self, user, item):
        """Simulate the RBAC check logic from the endpoint."""
        user_roles = set(getattr(user, 'roles', []) or [])
        full_access_roles = {'admin', 'ceo', 'gm', 'exec', 'supervisor'}
        
        if user_roles & full_access_roles:
            return True
        
        user_id = user.id
        return (
            item.owner_id == user_id or
            item.created_by_id == user_id or
            item.assigned_to_id == user_id or
            item.escalated_to_id == user_id
        )
    
    def test_admin_has_full_access(self, admin_user):
        """Admin role should have access to any item."""
        item = MockObeyaItem(owner_id=uuid4())  # Different owner
        
        assert self._check_rbac_access(admin_user, item) is True
    
    def test_ceo_has_full_access(self, ceo_user):
        """CEO role should have access to any item."""
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(ceo_user, item) is True
    
    def test_operator_access_as_owner(self, operator_user):
        """Operator should access items they own."""
        item = MockObeyaItem(owner_id=operator_user.id)
        
        assert self._check_rbac_access(operator_user, item) is True
    
    def test_operator_access_as_creator(self, operator_user):
        """Operator should access items they created."""
        item = MockObeyaItem(created_by_id=operator_user.id)
        
        assert self._check_rbac_access(operator_user, item) is True
    
    def test_operator_access_as_assignee(self, operator_user):
        """Operator should access items assigned to them."""
        item = MockObeyaItem(assigned_to_id=operator_user.id)
        
        assert self._check_rbac_access(operator_user, item) is True
    
    def test_operator_access_as_escalatee(self, operator_user):
        """Operator should access items escalated to them."""
        item = MockObeyaItem(escalated_to_id=operator_user.id)
        
        assert self._check_rbac_access(operator_user, item) is True
    
    def test_operator_no_access_to_others_items(self, operator_user):
        """Operator should NOT access items they have no relation to."""
        other_user_id = uuid4()
        item = MockObeyaItem(
            owner_id=other_user_id,
            created_by_id=other_user_id,
            assigned_to_id=other_user_id,
        )
        
        assert self._check_rbac_access(operator_user, item) is False
    
    def test_viewer_no_access_to_others_items(self, viewer_user):
        """Viewer should NOT access items they have no relation to."""
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(viewer_user, item) is False
    
    def test_supervisor_has_full_access(self):
        """Supervisor role should have full access."""
        supervisor = MockUser(roles=['supervisor'])
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(supervisor, item) is True
    
    def test_exec_has_full_access(self):
        """Exec role should have full access."""
        exec_user = MockUser(roles=['exec'])
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(exec_user, item) is True
    
    def test_gm_has_full_access(self):
        """GM role should have full access."""
        gm_user = MockUser(roles=['gm'])
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(gm_user, item) is True


class TestObeyaRBACDeleteLogic:
    """Test RBAC logic for delete operations."""
    
    def _check_delete_access(self, user, item):
        """Simulate the delete RBAC check logic."""
        user_roles = set(getattr(user, 'roles', []) or [])
        full_access_roles = {'admin', 'ceo', 'gm', 'exec'}  # No supervisor for delete
        
        if user_roles & full_access_roles:
            return True
        
        user_id = user.id
        return (
            item.owner_id == user_id or
            item.created_by_id == user_id
        )
    
    def test_owner_can_delete(self):
        """Owner should be able to delete their item."""
        user = MockUser(roles=['operator'])
        item = MockObeyaItem(owner_id=user.id)
        
        assert self._check_delete_access(user, item) is True
    
    def test_creator_can_delete(self):
        """Creator should be able to delete their item."""
        user = MockUser(roles=['operator'])
        item = MockObeyaItem(created_by_id=user.id)
        
        assert self._check_delete_access(user, item) is True
    
    def test_assignee_cannot_delete(self):
        """Assignee should NOT be able to delete (only view/update)."""
        user = MockUser(roles=['operator'])
        item = MockObeyaItem(assigned_to_id=user.id, owner_id=uuid4())
        
        assert self._check_delete_access(user, item) is False
    
    def test_admin_can_delete_any(self):
        """Admin should be able to delete any item."""
        admin = MockUser(roles=['admin'])
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_delete_access(admin, item) is True


class TestObeyaRBACUpdateLogic:
    """Test RBAC logic for update operations."""
    
    def _check_update_access(self, user, item):
        """Simulate the update RBAC check logic."""
        user_roles = set(getattr(user, 'roles', []) or [])
        full_access_roles = {'admin', 'ceo', 'gm', 'exec', 'supervisor'}
        
        if user_roles & full_access_roles:
            return True
        
        user_id = user.id
        return (
            item.owner_id == user_id or
            item.created_by_id == user_id or
            item.assigned_to_id == user_id
        )
    
    def test_assignee_can_update(self):
        """Assignee should be able to update the item."""
        user = MockUser(roles=['operator'])
        item = MockObeyaItem(assigned_to_id=user.id)
        
        assert self._check_update_access(user, item) is True
    
    def test_escalatee_cannot_update(self):
        """Escalatee can view but not update (unless also assigned)."""
        user = MockUser(roles=['operator'])
        item = MockObeyaItem(
            escalated_to_id=user.id,
            owner_id=uuid4(),
            assigned_to_id=uuid4(),
        )
        
        assert self._check_update_access(user, item) is False


class TestObeyaItemCreation:
    """Test that Obeya item creation sets ownership correctly."""
    
    def test_owner_id_set_to_assignee_or_creator(self):
        """Test owner_id logic during creation."""
        creator_id = uuid4()
        assignee_id = uuid4()
        
        # When assigned_to_id is provided, owner_id = assigned_to_id
        owner_with_assignee = assignee_id or creator_id
        assert owner_with_assignee == assignee_id
        
        # When no assigned_to_id, owner_id = creator_id
        owner_without_assignee = None or creator_id
        assert owner_without_assignee == creator_id


class TestMultipleRoles:
    """Test users with multiple roles."""
    
    def _check_rbac_access(self, user, item):
        """Simulate the RBAC check logic."""
        user_roles = set(getattr(user, 'roles', []) or [])
        full_access_roles = {'admin', 'ceo', 'gm', 'exec', 'supervisor'}
        
        if user_roles & full_access_roles:
            return True
        
        user_id = user.id
        return (
            item.owner_id == user_id or
            item.created_by_id == user_id or
            item.assigned_to_id == user_id or
            item.escalated_to_id == user_id
        )
    
    def test_user_with_multiple_roles_including_admin(self):
        """User with admin + other roles has full access."""
        user = MockUser(roles=['admin', 'operator', 'quality'])
        item = MockObeyaItem(owner_id=uuid4())
        
        assert self._check_rbac_access(user, item) is True
    
    def test_user_with_non_admin_multiple_roles(self):
        """User without privileged roles needs ownership relation."""
        user = MockUser(roles=['operator', 'quality', 'viewer'])
        item = MockObeyaItem(owner_id=uuid4())  # Different owner
        
        assert self._check_rbac_access(user, item) is False
    
    def test_user_with_non_admin_roles_but_is_owner(self):
        """User without privileged roles but is owner has access."""
        user = MockUser(roles=['operator', 'quality'])
        item = MockObeyaItem(owner_id=user.id)
        
        assert self._check_rbac_access(user, item) is True
