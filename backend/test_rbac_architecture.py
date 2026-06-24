"""
RBAC Architecture Smoke Tests
----------------------------------
Validates the entire RBAC system without requiring a running database.
Tests role normalization, permission matrix, policy enforcement,
branch isolation, and privilege escalation prevention.

Run with: python -m pytest test_rbac_architecture.py -v
"""

import sys
import os

# Ensure app is importable
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/")
os.environ.setdefault("JWT_SECRET", "test-secret")


class TestRoleEnum:
    """Test the Role enum and normalization."""

    def test_canonical_roles_exist(self):
        from app.roles.enums import Role
        assert Role.SUPER_ADMIN.value == "super_admin"
        assert Role.BRANCH_MANAGER.value == "branch_manager"
        assert Role.KITCHEN_STAFF.value == "kitchen_staff"
        assert Role.DELIVERY_AGENT.value == "delivery_agent"
        assert Role.CUSTOMER.value == "customer"

    def test_all_canonical_returns_five(self):
        from app.roles.enums import Role
        canonical = Role.all_canonical()
        assert len(canonical) == 5
        assert Role.SUPER_ADMIN in canonical
        assert Role.CUSTOMER in canonical

    def test_normalize_canonical(self):
        from app.roles.enums import Role
        assert Role.normalize("super_admin") == Role.SUPER_ADMIN
        assert Role.normalize("customer") == Role.CUSTOMER

    def test_normalize_legacy_admin(self):
        from app.roles.enums import Role
        assert Role.normalize("admin") == Role.SUPER_ADMIN

    def test_normalize_legacy_manager(self):
        from app.roles.enums import Role
        assert Role.normalize("manager") == Role.BRANCH_MANAGER

    def test_normalize_legacy_delivery(self):
        from app.roles.enums import Role
        assert Role.normalize("delivery") == Role.DELIVERY_AGENT

    def test_normalize_legacy_agent(self):
        from app.roles.enums import Role
        assert Role.normalize("agent") == Role.DELIVERY_AGENT

    def test_normalize_unknown_raises(self):
        from app.roles.enums import Role
        import pytest
        with pytest.raises(ValueError, match="Unknown role"):
            Role.normalize("wizard")

    def test_display_names(self):
        from app.roles.enums import Role
        assert Role.SUPER_ADMIN.display_name == "Super Admin"
        assert Role.BRANCH_MANAGER.display_name == "Branch Manager"
        assert Role.KITCHEN_STAFF.display_name == "Kitchen Staff"
        assert Role.DELIVERY_AGENT.display_name == "Delivery Agent"
        assert Role.CUSTOMER.display_name == "Customer"

    def test_hierarchy_ordering(self):
        from app.roles.enums import Role
        assert Role.SUPER_ADMIN > Role.BRANCH_MANAGER
        assert Role.BRANCH_MANAGER > Role.KITCHEN_STAFF
        assert Role.KITCHEN_STAFF > Role.DELIVERY_AGENT
        assert Role.DELIVERY_AGENT > Role.CUSTOMER

    def test_no_legacy_enum_members(self):
        """Ensure legacy values are NOT enum members."""
        from app.roles.enums import Role
        canonical = Role.all_canonical()
        # Only 5 canonical roles should exist
        assert len(list(Role)) == 5
        for role in Role:
            assert role in canonical


class TestPermissions:
    """Test the permission matrix and helper utilities."""

    def test_super_admin_has_all_permissions(self):
        from app.roles.enums import Role, Permission
        from app.roles.permissions import ROLE_PERMISSIONS
        admin_perms = ROLE_PERMISSIONS[Role.SUPER_ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"SUPER_ADMIN missing {perm}"

    def test_customer_cannot_manage_agents(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert not has_permission("customer", Permission.AGENTS_CREATE)
        assert not has_permission("customer", Permission.AGENTS_DELETE)

    def test_customer_can_browse_menu(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("customer", Permission.MENU_READ)

    def test_customer_can_create_orders(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("customer", Permission.ORDERS_CREATE)

    def test_delivery_cannot_assign_orders(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert not has_permission("delivery_agent", Permission.ORDERS_ASSIGN)

    def test_delivery_can_update_delivery_status(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("delivery_agent", Permission.ORDERS_UPDATE_DELIVERY_STATUS)

    def test_kitchen_staff_can_read_orders(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("kitchen_staff", Permission.ORDERS_READ)

    def test_kitchen_staff_cannot_delete_agents(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert not has_permission("kitchen_staff", Permission.AGENTS_DELETE)

    def test_branch_manager_can_manage_agents(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("branch_manager", Permission.AGENTS_CREATE)
        assert has_permission("branch_manager", Permission.AGENTS_READ)
        assert has_permission("branch_manager", Permission.AGENTS_DELETE)

    def test_has_any_permission(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_any_permission
        assert has_any_permission("customer", Permission.MENU_READ, Permission.AGENTS_DELETE)
        assert not has_any_permission("customer", Permission.AGENTS_CREATE, Permission.AGENTS_DELETE)

    def test_has_all_permissions(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_all_permissions
        assert has_all_permissions("customer", Permission.MENU_READ, Permission.ORDERS_CREATE)
        assert not has_all_permissions("customer", Permission.MENU_READ, Permission.AGENTS_CREATE)

    def test_legacy_role_string_permissions(self):
        """Legacy 'admin' string should resolve to SUPER_ADMIN permissions."""
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert has_permission("admin", Permission.SYSTEM_INTERNAL)
        assert has_permission("manager", Permission.AGENTS_READ)
        assert has_permission("delivery", Permission.ORDERS_UPDATE_DELIVERY_STATUS)

    def test_unknown_role_has_no_permissions(self):
        from app.roles.enums import Permission
        from app.roles.permissions import has_permission
        assert not has_permission("wizard", Permission.ORDERS_READ)

    def test_permission_resource_action(self):
        from app.roles.enums import Permission
        assert Permission.ORDERS_CREATE.resource == "orders"
        assert Permission.ORDERS_CREATE.action == "create"
        assert Permission.AGENTS_DELETE.resource == "agents"
        assert Permission.AGENTS_DELETE.action == "delete"


class TestRoleGroupings:
    """Test role classification helpers."""

    def test_internal_roles(self):
        from app.roles.enums import Role
        from app.roles.permissions import INTERNAL_ROLES
        assert Role.SUPER_ADMIN in INTERNAL_ROLES
        assert Role.BRANCH_MANAGER in INTERNAL_ROLES
        assert Role.KITCHEN_STAFF in INTERNAL_ROLES
        assert Role.DELIVERY_AGENT in INTERNAL_ROLES
        assert Role.CUSTOMER not in INTERNAL_ROLES

    def test_branch_required_roles(self):
        from app.roles.permissions import requires_branch
        assert requires_branch("branch_manager")
        assert requires_branch("kitchen_staff")
        assert requires_branch("delivery_agent")
        assert not requires_branch("super_admin")
        assert not requires_branch("customer")

    def test_is_internal_role(self):
        from app.roles.permissions import is_internal_role
        assert is_internal_role("super_admin")
        assert is_internal_role("branch_manager")
        assert not is_internal_role("customer")
        # Legacy values
        assert is_internal_role("admin")
        assert is_internal_role("manager")

    def test_can_manage_users(self):
        from app.roles.permissions import can_manage_users
        assert can_manage_users("super_admin")
        assert can_manage_users("branch_manager")
        assert not can_manage_users("kitchen_staff")
        assert not can_manage_users("delivery_agent")
        assert not can_manage_users("customer")


class TestPrivilegeEscalation:
    """Test privilege escalation prevention."""

    def test_super_admin_can_assign_any_role(self):
        from app.roles.enums import Role
        from app.roles.permissions import get_manageable_roles
        manageable = get_manageable_roles("super_admin")
        assert Role.SUPER_ADMIN in manageable
        assert Role.BRANCH_MANAGER in manageable
        assert Role.CUSTOMER in manageable

    def test_manager_cannot_create_admin(self):
        from app.roles.enums import Role
        from app.roles.permissions import get_manageable_roles
        manageable = get_manageable_roles("branch_manager")
        assert Role.SUPER_ADMIN not in manageable
        assert Role.BRANCH_MANAGER not in manageable

    def test_manager_can_create_staff(self):
        from app.roles.enums import Role
        from app.roles.permissions import get_manageable_roles
        manageable = get_manageable_roles("branch_manager")
        assert Role.KITCHEN_STAFF in manageable
        assert Role.DELIVERY_AGENT in manageable

    def test_kitchen_staff_cannot_manage_anyone(self):
        from app.roles.permissions import get_manageable_roles
        assert get_manageable_roles("kitchen_staff") == []

    def test_customer_cannot_manage_anyone(self):
        from app.roles.permissions import get_manageable_roles
        assert get_manageable_roles("customer") == []


class TestBranchIsolation:
    """Test the BranchIsolationFilter query builder."""

    def _make_user(self, role, branch_id=None, user_id="user123"):
        from app.dependencies.auth import CurrentUser
        return CurrentUser(
            user_id=user_id,
            role=role,
            branch_id=branch_id,
        )

    def test_super_admin_no_filter(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("super_admin")
        iso = BranchIsolationFilter(user)
        assert iso.order_filter() == {}
        assert iso.agent_filter() == {}

    def test_branch_manager_branch_scoped(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("branch_manager", branch_id="b1")
        iso = BranchIsolationFilter(user)
        assert iso.order_filter() == {"branch_id": "b1"}
        assert iso.agent_filter() == {"branch_id": "b1"}

    def test_kitchen_staff_branch_scoped(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("kitchen_staff", branch_id="b2")
        iso = BranchIsolationFilter(user)
        assert iso.order_filter() == {"branch_id": "b2"}

    def test_delivery_agent_assignment_scoped(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("delivery_agent", user_id="agent1")
        iso = BranchIsolationFilter(user)
        order_filter = iso.order_filter()
        assert "$or" in order_filter
        assert {"assigned_delivery_id": "agent1"} in order_filter["$or"]
        assert {"assigned_agent_id": "agent1"} in order_filter["$or"]

    def test_customer_self_scoped(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("customer", user_id="cust1")
        iso = BranchIsolationFilter(user)
        assert iso.order_filter() == {"customer_user_id": "cust1"}

    def test_customer_can_browse_active_branches(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("customer")
        iso = BranchIsolationFilter(user)
        branch_q = iso.branch_filter()
        assert branch_q.get("status") == "active"
        assert branch_q.get("is_active") is True

    def test_extra_filters_merge(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("branch_manager", branch_id="b1")
        iso = BranchIsolationFilter(user)
        result = iso.order_filter(extra={"status": "placed"})
        assert "$and" in result
        assert {"branch_id": "b1"} in result["$and"]
        assert {"status": "placed"} in result["$and"]

    def test_unknown_role_denied(self):
        from app.middleware.branch_isolation import BranchIsolationFilter
        user = self._make_user("wizard")
        iso = BranchIsolationFilter(user)
        assert iso.order_filter() == {"_id": None}


class TestQueryFilterBuilders:
    """Test the dependency-level query filter builders."""

    def _make_user(self, role, branch_id=None, user_id="user123"):
        from app.dependencies.auth import CurrentUser
        return CurrentUser(
            user_id=user_id,
            role=role,
            branch_id=branch_id,
        )

    def test_build_order_filter_admin(self):
        from app.dependencies.auth import build_order_filter
        user = self._make_user("super_admin")
        assert build_order_filter(user) == {}

    def test_build_order_filter_manager(self):
        from app.dependencies.auth import build_order_filter
        user = self._make_user("branch_manager", branch_id="b1")
        assert build_order_filter(user) == {"branch_id": "b1"}

    def test_build_agent_filter_delivery(self):
        from app.dependencies.auth import build_agent_filter
        user = self._make_user("delivery_agent", user_id="d1")
        result = build_agent_filter(user)
        assert "$or" in result

    def test_build_user_filter_manager(self):
        from app.dependencies.auth import build_user_filter
        user = self._make_user("branch_manager", branch_id="b3")
        assert build_user_filter(user) == {"branch_id": "b3"}

    def test_build_user_filter_self(self):
        from app.dependencies.auth import build_user_filter
        user = self._make_user("delivery_agent", user_id="d1")
        result = build_user_filter(user)
        assert "$or" in result


class TestModuleImports:
    """Verify all expected modules are importable."""

    def test_import_config(self):
        from app.config import settings
        assert settings.APP_NAME == "Cloud Kitchen API"

    def test_import_roles(self):
        from app.roles import Role, Permission, has_permission

    def test_import_permissions_package(self):
        from app.permissions import Role, Permission, has_permission

    def test_import_middleware(self):
        from app.middleware import (
            RBACMiddleware,
            require_permissions,
            require_any_permission,
            require_role,
            BranchIsolationFilter,
            RequestContextMiddleware,
            SecurityHeadersMiddleware,
        )

    def test_import_models(self):
        from app.models import (
            Branch, BranchCreate, BranchUpdate, BranchStatus,
            UserDocument, UserCreate, UserUpdate, UserResponse,
            OrderCreate, OrderStatusUpdate,
            AgentCreate, AgentUpdate,
        )

    def test_import_backward_compat_auth(self):
        from app.auth import (
            create_access_token,
            decode_token,
            hash_password,
            verify_password,
        )
        from app.dependencies.auth import (
            CurrentUser,
            get_current_user,
            get_current_user_optional,
            build_order_filter,
            build_agent_filter,
            build_user_filter,
        )

    def test_import_dependencies(self):
        from app.dependencies.auth import (
            CurrentUser,
            get_current_user,
            get_current_user_optional,
            build_order_filter,
            build_agent_filter,
            build_user_filter,
        )

    def test_import_services(self):
        from app.services.user_service import UserService
        from app.services.branch_service import (
            get_all_branches,
            get_branch_by_id,
            create_branch,
            update_branch,
            delete_branch,
        )
