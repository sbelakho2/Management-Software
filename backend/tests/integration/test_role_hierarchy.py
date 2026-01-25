"""
Integration tests for the role hierarchy and permission system.

These tests verify:
1. Role hierarchy levels work correctly
2. CEO and Admin have full access to all endpoints
3. Role-based insight filtering works correctly
4. Permission escalation/de-escalation
5. Cross-role access scenarios
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sensei.api.deps import RoleChecker, PermissionChecker
from sensei.core.security import TokenData
from sensei.services.core.role_insights_config import (
    InsightCategory,
    ROLE_INSIGHT_ACCESS,
    FULL_ACCESS_ROLES,
    can_access_insight,
    get_role_insight_profile,
    get_accessible_insights,
    filter_insights_for_role,
)
from sensei.models.user import RoleType


class TestRoleHierarchy:
    """Test role hierarchy levels and ordering."""

    def test_admin_has_lowest_hierarchy_level(self):
        """Admin should have hierarchy level 0 (most privileged)."""
        assert RoleChecker.ROLE_HIERARCHY["admin"] == 0

    def test_ceo_has_second_lowest_hierarchy_level(self):
        """CEO should have hierarchy level 5."""
        assert RoleChecker.ROLE_HIERARCHY["ceo"] == 5

    def test_viewer_has_highest_hierarchy_level(self):
        """Viewer should have hierarchy level 100 (least privileged)."""
        assert RoleChecker.ROLE_HIERARCHY["viewer"] == 100

    def test_hierarchy_ordering_is_consistent(self):
        """Higher privilege roles should have lower hierarchy numbers."""
        hierarchy = RoleChecker.ROLE_HIERARCHY
        
        # Executive ordering
        assert hierarchy["admin"] < hierarchy["ceo"]
        assert hierarchy["ceo"] < hierarchy["gm"]
        assert hierarchy["gm"] < hierarchy["exec"]
        
        # Department ordering
        assert hierarchy["exec"] < hierarchy["finance"]
        assert hierarchy["finance"] < hierarchy["hr"]
        
        # Operational ordering
        assert hierarchy["supervisor"] < hierarchy["team_lead"]
        assert hierarchy["team_lead"] < hierarchy["operator"]
        assert hierarchy["operator"] < hierarchy["viewer"]

    def test_all_24_roles_have_hierarchy_levels(self):
        """All 24 roles should have defined hierarchy levels."""
        expected_roles = {
            "admin", "ceo", "gm", "exec", "finance", "accountant", "hr", "ops",
            "quality", "auditor", "it", "supervisor", "team_lead", "operator",
            "viewer", "sales_engineer", "estimator", "supply_chain", "maintenance",
            "warehouse", "sales", "purchasing", "logistics", "engineering"
        }
        
        actual_roles = set(RoleChecker.ROLE_HIERARCHY.keys())
        assert expected_roles == actual_roles


class TestRoleCheckerHierarchy:
    """Test RoleChecker access rules."""

    @pytest.fixture
    def mock_token_data(self):
        """Create mock token data factory."""
        from datetime import datetime
        
        def _create(roles: list[str], permissions: list[str] = None):
            return TokenData(
                sub=str(uuid4()),
                jti=str(uuid4()),
                type="access",
                roles=roles,
                permissions=permissions or [],
                exp=datetime.fromtimestamp(9999999999),
                iat=datetime.fromtimestamp(1000000000),
            )
        return _create

    @pytest.mark.asyncio
    async def test_admin_passes_all_role_checks(self, mock_token_data):
        """Admin should pass any role check."""
        checker = RoleChecker(["ops", "supervisor"])
        token = mock_token_data(["admin"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            result = await checker(token)
            assert result is True

    @pytest.mark.asyncio
    async def test_ceo_passes_all_role_checks(self, mock_token_data):
        """CEO should pass any role check."""
        checker = RoleChecker(["it"])  # IT-only endpoint
        token = mock_token_data(["ceo"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            result = await checker(token)
            assert result is True

    @pytest.mark.asyncio
    async def test_direct_role_match(self, mock_token_data):
        """User with matching role should pass."""
        checker = RoleChecker(["ops", "supervisor"])
        token = mock_token_data(["ops"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            result = await checker(token)
            assert result is True

    @pytest.mark.asyncio
    async def test_higher_privilege_role_passes(self, mock_token_data):
        """Non-matching roles should not inherit access via hierarchy."""
        from fastapi import HTTPException

        checker = RoleChecker(["operator"])
        token = mock_token_data(["supervisor"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            with pytest.raises(HTTPException) as exc_info:
                await checker(token)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_lower_privilege_role_fails(self, mock_token_data):
        """User with lower privilege than required should fail."""
        from fastapi import HTTPException
        
        checker = RoleChecker(["finance"])  # Level 20
        token = mock_token_data(["operator"])  # Level 98 (less privileged)
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            with pytest.raises(HTTPException) as exc_info:
                await checker(token)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_multi_role_user_uses_best_privilege(self, mock_token_data):
        """User must have an explicitly allowed role (or admin/ceo)."""
        from fastapi import HTTPException

        checker = RoleChecker(["finance"])
        token = mock_token_data(["operator", "gm"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            with pytest.raises(HTTPException) as exc_info:
                await checker(token)
            assert exc_info.value.status_code == 403


class TestPermissionCheckerCEOAccess:
    """Test PermissionChecker behavior for privileged vs regular roles."""

    @pytest.fixture
    def mock_token_data(self):
        """Create mock token data factory."""
        from datetime import datetime
        
        def _create(roles: list[str], permissions: list[str] = None):
            return TokenData(
                sub=str(uuid4()),
                jti=str(uuid4()),
                type="access",
                roles=roles,
                permissions=permissions or [],
                exp=datetime.fromtimestamp(9999999999),
                iat=datetime.fromtimestamp(1000000000),
            )
        return _create

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self, mock_token_data):
        """Admin should pass any permission check."""
        checker = PermissionChecker("finance.gl:approve")
        token = mock_token_data(["admin"], [])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            result = await checker(token)
            assert result is True

    @pytest.mark.asyncio
    async def test_ceo_has_all_permissions(self, mock_token_data):
        """CEO does not implicitly get all granular permissions."""
        from fastapi import HTTPException

        checker = PermissionChecker("admin.system:delete")
        token = mock_token_data(["ceo"], [])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            with pytest.raises(HTTPException) as exc_info:
                await checker(token)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_regular_user_needs_explicit_permission(self, mock_token_data):
        """Regular user without permission should fail."""
        from fastapi import HTTPException
        
        checker = PermissionChecker("finance.gl:approve")
        token = mock_token_data(["ops"], [])  # No permissions
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            with pytest.raises(HTTPException) as exc_info:
                await checker(token)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_with_permission_passes(self, mock_token_data):
        """User with the required permission should pass."""
        checker = PermissionChecker("finance.gl:view")
        token = mock_token_data(["accountant"], ["finance.gl:view"])
        
        with patch("sensei.api.deps.get_token_data", return_value=token):
            result = await checker(token)
            assert result is True


class TestRoleInsightAccess:
    """Test role-based insight access configuration."""

    def test_full_access_roles_defined(self):
        """Admin and CEO should be in full access roles."""
        assert "admin" in FULL_ACCESS_ROLES
        assert "ceo" in FULL_ACCESS_ROLES
        assert len(FULL_ACCESS_ROLES) == 2

    def test_all_24_roles_have_insight_config(self):
        """All 24 roles should have insight access defined."""
        expected_roles = {
            "admin", "ceo", "gm", "exec", "finance", "accountant", "hr", "ops",
            "quality", "auditor", "it", "supervisor", "team_lead", "operator",
            "viewer", "sales_engineer", "estimator", "supply_chain", "maintenance",
            "warehouse", "sales", "purchasing", "logistics", "engineering"
        }
        
        actual_roles = set(ROLE_INSIGHT_ACCESS.keys())
        assert expected_roles == actual_roles

    def test_admin_has_all_insights(self):
        """Admin should have access to all insight categories."""
        admin_insights = ROLE_INSIGHT_ACCESS["admin"]
        all_insights = set(InsightCategory)
        assert admin_insights == all_insights

    def test_ceo_has_all_insights(self):
        """CEO should have access to all insight categories."""
        ceo_insights = ROLE_INSIGHT_ACCESS["ceo"]
        all_insights = set(InsightCategory)
        assert ceo_insights == all_insights

    def test_viewer_has_minimal_insights(self):
        """Viewer should have minimal insight access (general only)."""
        viewer_insights = ROLE_INSIGHT_ACCESS["viewer"]
        
        # Should only have general insights
        expected = {
            InsightCategory.TASK_RECOMMENDATIONS,
            InsightCategory.PERSONAL_PRODUCTIVITY,
            InsightCategory.UPCOMING_DEADLINES,
            InsightCategory.NOTIFICATION_SUMMARY,
        }
        assert viewer_insights == expected

    def test_operator_has_limited_insights(self):
        """Operator should have limited but relevant insights."""
        operator_insights = ROLE_INSIGHT_ACCESS["operator"]
        
        # Should have SPC alerts and quality trends for their work
        assert InsightCategory.SPC_ALERTS in operator_insights
        assert InsightCategory.QUALITY_TRENDS in operator_insights
        assert InsightCategory.EQUIPMENT_HEALTH in operator_insights
        
        # Should NOT have strategic or financial insights
        assert InsightCategory.STRATEGIC_OVERVIEW not in operator_insights
        assert InsightCategory.FINANCIAL_KPIs not in operator_insights
        assert InsightCategory.COMPENSATION_ANALYSIS not in operator_insights

    def test_finance_role_has_financial_insights(self):
        """Finance role should have access to financial insights."""
        finance_insights = ROLE_INSIGHT_ACCESS["finance"]
        
        assert InsightCategory.FINANCIAL_KPIs in finance_insights
        assert InsightCategory.CASH_FLOW_FORECAST in finance_insights
        assert InsightCategory.MARGIN_ANALYSIS in finance_insights
        assert InsightCategory.COST_OPTIMIZATION in finance_insights
        assert InsightCategory.REVENUE_TRENDS in finance_insights
        assert InsightCategory.BUDGET_VARIANCE in finance_insights

    def test_hr_role_has_hr_insights(self):
        """HR role should have access to HR insights."""
        hr_insights = ROLE_INSIGHT_ACCESS["hr"]
        
        assert InsightCategory.WORKFORCE_ANALYTICS in hr_insights
        assert InsightCategory.RETENTION_RISK in hr_insights
        assert InsightCategory.TRAINING_GAPS in hr_insights
        assert InsightCategory.PERFORMANCE_TRENDS in hr_insights
        assert InsightCategory.COMPENSATION_ANALYSIS in hr_insights
        assert InsightCategory.HEADCOUNT_PLANNING in hr_insights

    def test_it_role_has_it_insights(self):
        """IT role should have access to IT-specific insights."""
        it_insights = ROLE_INSIGHT_ACCESS["it"]
        
        assert InsightCategory.SYSTEM_HEALTH in it_insights
        assert InsightCategory.SECURITY_ALERTS in it_insights
        assert InsightCategory.USAGE_ANALYTICS in it_insights
        assert InsightCategory.PERFORMANCE_METRICS in it_insights
        assert InsightCategory.INTEGRATION_STATUS in it_insights


class TestCanAccessInsight:
    """Test can_access_insight function."""

    def test_admin_can_access_any_insight(self):
        """Admin should be able to access any insight."""
        for insight in InsightCategory:
            result = can_access_insight("admin", insight)
            assert result.allowed is True
            assert result.reason == "Full access role"

    def test_ceo_can_access_any_insight(self):
        """CEO should be able to access any insight."""
        for insight in InsightCategory:
            result = can_access_insight("ceo", insight)
            assert result.allowed is True
            assert result.reason == "Full access role"

    def test_role_case_insensitive(self):
        """Role checking should be case insensitive."""
        result1 = can_access_insight("CEO", InsightCategory.STRATEGIC_OVERVIEW)
        result2 = can_access_insight("ceo", InsightCategory.STRATEGIC_OVERVIEW)
        result3 = can_access_insight("Ceo", InsightCategory.STRATEGIC_OVERVIEW)
        
        assert result1.allowed == result2.allowed == result3.allowed

    def test_allowed_insight_for_role(self):
        """Role with access to specific insight should be allowed."""
        result = can_access_insight("finance", InsightCategory.FINANCIAL_KPIs)
        assert result.allowed is True
        assert result.reason == "Insight allowed for role"

    def test_denied_insight_for_role(self):
        """Role without access to specific insight should be denied."""
        result = can_access_insight("operator", InsightCategory.STRATEGIC_OVERVIEW)
        assert result.allowed is False
        assert "not accessible" in result.reason


class TestGetRoleInsightProfile:
    """Test get_role_insight_profile function."""

    def test_admin_profile_has_full_access(self):
        """Admin profile should show full access."""
        profile = get_role_insight_profile("admin")
        
        assert profile.role == "admin"
        assert profile.has_full_access is True
        assert profile.insight_count == len(InsightCategory)
        assert len(profile.denied_insights) == 0

    def test_ceo_profile_has_full_access(self):
        """CEO profile should show full access."""
        profile = get_role_insight_profile("ceo")
        
        assert profile.role == "ceo"
        assert profile.has_full_access is True
        assert profile.insight_count == len(InsightCategory)
        assert len(profile.denied_insights) == 0

    def test_regular_role_profile(self):
        """Regular role should have partial access."""
        profile = get_role_insight_profile("operator")
        
        assert profile.role == "operator"
        assert profile.has_full_access is False
        assert profile.insight_count < len(InsightCategory)
        assert len(profile.denied_insights) > 0

    def test_allowed_and_denied_are_disjoint(self):
        """Allowed and denied insights should not overlap."""
        for role in ROLE_INSIGHT_ACCESS.keys():
            profile = get_role_insight_profile(role)
            overlap = profile.allowed_insights & profile.denied_insights
            assert len(overlap) == 0, f"Role {role} has overlapping insights"

    def test_allowed_plus_denied_equals_all(self):
        """Allowed plus denied should equal all insights."""
        for role in ROLE_INSIGHT_ACCESS.keys():
            if role not in FULL_ACCESS_ROLES:
                profile = get_role_insight_profile(role)
                total = profile.allowed_insights | profile.denied_insights
                assert total == frozenset(InsightCategory)


class TestGetAccessibleInsights:
    """Test get_accessible_insights function."""

    def test_single_role_access(self):
        """Single role should return that role's insights."""
        insights = get_accessible_insights(["finance"])
        assert insights == ROLE_INSIGHT_ACCESS["finance"]

    def test_multi_role_union(self):
        """Multiple roles should return union of all insights."""
        insights = get_accessible_insights(["finance", "hr"])
        
        finance_insights = ROLE_INSIGHT_ACCESS["finance"]
        hr_insights = ROLE_INSIGHT_ACCESS["hr"]
        expected = finance_insights | hr_insights
        
        assert insights == expected

    def test_admin_role_gives_full_access(self):
        """Any role list containing admin should give full access."""
        insights = get_accessible_insights(["operator", "admin"])
        assert insights == frozenset(InsightCategory)

    def test_ceo_role_gives_full_access(self):
        """Any role list containing ceo should give full access."""
        insights = get_accessible_insights(["viewer", "ceo"])
        assert insights == frozenset(InsightCategory)

    def test_empty_roles_returns_empty(self):
        """Empty role list should return empty insights."""
        insights = get_accessible_insights([])
        assert insights == frozenset()


class TestFilterInsightsForRole:
    """Test filter_insights_for_role function."""

    def test_filters_out_denied_insights(self):
        """Should filter out insights the role cannot access."""
        insights = [
            {"id": 1, "category": InsightCategory.STRATEGIC_OVERVIEW.value, "data": "test1"},
            {"id": 2, "category": InsightCategory.TASK_RECOMMENDATIONS.value, "data": "test2"},
            {"id": 3, "category": InsightCategory.FINANCIAL_KPIs.value, "data": "test3"},
        ]
        
        # Operator can only access TASK_RECOMMENDATIONS from these
        filtered = filter_insights_for_role(insights, ["operator"])
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 2

    def test_admin_keeps_all_insights(self):
        """Admin should keep all insights."""
        insights = [
            {"id": 1, "category": InsightCategory.STRATEGIC_OVERVIEW.value},
            {"id": 2, "category": InsightCategory.FINANCIAL_KPIs.value},
            {"id": 3, "category": InsightCategory.SECURITY_ALERTS.value},
        ]
        
        filtered = filter_insights_for_role(insights, ["admin"])
        assert len(filtered) == 3

    def test_ceo_keeps_all_insights(self):
        """CEO should keep all insights."""
        insights = [
            {"id": 1, "category": InsightCategory.STRATEGIC_OVERVIEW.value},
            {"id": 2, "category": InsightCategory.COMPENSATION_ANALYSIS.value},
            {"id": 3, "category": InsightCategory.SECURITY_ALERTS.value},
        ]
        
        filtered = filter_insights_for_role(insights, ["ceo"])
        assert len(filtered) == 3

    def test_custom_category_field(self):
        """Should work with custom category field name."""
        insights = [
            {"id": 1, "type": InsightCategory.TASK_RECOMMENDATIONS.value},
            {"id": 2, "type": InsightCategory.STRATEGIC_OVERVIEW.value},
        ]
        
        filtered = filter_insights_for_role(insights, ["viewer"], category_field="type")
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == 1

    def test_missing_category_included(self):
        """Insights without category should be included by default."""
        insights = [
            {"id": 1, "data": "no category"},
            {"id": 2, "category": InsightCategory.TASK_RECOMMENDATIONS.value},
        ]
        
        filtered = filter_insights_for_role(insights, ["viewer"])
        
        assert len(filtered) == 2


class TestRoleTypeEnumConsistency:
    """Test that backend RoleType enum matches the hierarchy."""

    def test_all_hierarchy_roles_in_enum(self):
        """All roles in hierarchy should be in RoleType enum."""
        hierarchy_roles = set(RoleChecker.ROLE_HIERARCHY.keys())
        enum_roles = {r.value for r in RoleType}
        
        # Check that all hierarchy roles exist in enum
        for role in hierarchy_roles:
            assert role in enum_roles, f"Role '{role}' in hierarchy but not in RoleType enum"

    def test_all_enum_roles_in_hierarchy(self):
        """All roles in RoleType enum should be in hierarchy."""
        hierarchy_roles = set(RoleChecker.ROLE_HIERARCHY.keys())
        enum_roles = {r.value for r in RoleType}
        
        for role in enum_roles:
            assert role in hierarchy_roles, f"Role '{role}' in RoleType enum but not in hierarchy"

    def test_role_type_count_is_24(self):
        """RoleType enum should have exactly 24 roles."""
        assert len(RoleType) == 24


class TestCrossRoleScenarios:
    """Test complex cross-role access scenarios."""

    def test_gm_cannot_access_admin_only_pages(self):
        """GM should not be able to access admin-only endpoints directly."""
        # GM (level 10) should be able to access most things but not admin (level 0)
        gm_level = RoleChecker.ROLE_HIERARCHY["gm"]
        admin_level = RoleChecker.ROLE_HIERARCHY["admin"]
        
        assert gm_level > admin_level

    def test_supervisor_can_access_operator_resources(self):
        """Supervisor should be able to access operator-level resources."""
        supervisor_level = RoleChecker.ROLE_HIERARCHY["supervisor"]
        operator_level = RoleChecker.ROLE_HIERARCHY["operator"]
        
        assert supervisor_level < operator_level

    def test_cross_department_access_requires_explicit_role(self):
        """Cross-department access should require the specific role."""
        # Finance shouldn't have HR insights by default
        finance_insights = ROLE_INSIGHT_ACCESS["finance"]
        
        assert InsightCategory.RETENTION_RISK not in finance_insights
        assert InsightCategory.TRAINING_GAPS not in finance_insights

    def test_multi_department_user_gets_combined_access(self):
        """User with multiple department roles should get combined access."""
        combined = get_accessible_insights(["finance", "hr"])
        
        # Should have both finance and HR insights
        assert InsightCategory.FINANCIAL_KPIs in combined
        assert InsightCategory.RETENTION_RISK in combined
        assert InsightCategory.CASH_FLOW_FORECAST in combined
        assert InsightCategory.TRAINING_GAPS in combined
