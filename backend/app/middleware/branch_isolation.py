"""
Branch Isolation Filter
-------------------------
Enforces data isolation between branches.

Provides a builder that constructs MongoDB query filters based on
the current user's role and branch assignment:

    SUPER_ADMIN    → no filter (sees all branches)
    BRANCH_MANAGER → branch_id == user.branch_id
    KITCHEN_STAFF  → branch_id == user.branch_id
    DELIVERY_AGENT → assigned_agent_id == user.user_id
    CUSTOMER       → customer-specific filter (e.g. customer_id)

Usage:
    from app.middleware.branch_isolation import BranchIsolationFilter

    iso = BranchIsolationFilter(user)
    query = iso.order_filter(extra={"status": "placed"})
    orders.find(query)
"""

import logging
from typing import Optional

from app.dependencies.auth import CurrentUser
from app.roles.enums import Role

logger = logging.getLogger(__name__)


class BranchIsolationFilter:
    """
    Builds MongoDB query filters that enforce branch-level data isolation.
    """

    def __init__(self, user: CurrentUser):
        self.user = user
        try:
            self.role = Role.normalize(user.role)
        except ValueError:
            self.role = None

    @property
    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    @property
    def is_branch_scoped(self) -> bool:
        return self.role in (Role.BRANCH_MANAGER, Role.KITCHEN_STAFF)

    @property
    def is_delivery(self) -> bool:
        return self.role == Role.DELIVERY_AGENT

    @property
    def is_customer(self) -> bool:
        return self.role == Role.CUSTOMER

    # ── Query builders ────────────────────────────────────────────────

    def _merge(self, scope: dict, extra: Optional[dict] = None) -> dict:
        """Merge a scope filter with optional extra criteria."""
        if not scope and not extra:
            return {}
        if not scope:
            return dict(extra or {})
        if not extra:
            return dict(scope)
        return {"$and": [dict(scope), dict(extra)]}

    def order_filter(self, extra: Optional[dict] = None) -> dict:
        """
        Build an order query filter scoped to the user's access level.
        """
        if self.is_super_admin:
            return dict(extra or {})

        if self.is_branch_scoped:
            scope = {"branch_id": self.user.branch_id}
            return self._merge(scope, extra)

        if self.is_delivery:
            scope = {
                "$or": [
                    {"assigned_delivery_id": self.user.user_id},
                    {"assigned_agent_id": self.user.user_id},
                ]
            }
            return self._merge(scope, extra)

        if self.is_customer:
            scope = {"customer_user_id": self.user.user_id}
            return self._merge(scope, extra)

        # Unknown role → deny all
        return {"_id": None}

    def agent_filter(self, extra: Optional[dict] = None) -> dict:
        """
        Build an agent query filter scoped to the user's access level.
        """
        if self.is_super_admin:
            return dict(extra or {})

        if self.is_branch_scoped:
            scope = {"branch_id": self.user.branch_id}
            return self._merge(scope, extra)

        if self.is_delivery:
            from bson.objectid import ObjectId
            identity_filters = [{"user_id": self.user.user_id}]
            try:
                identity_filters.append({"_id": ObjectId(self.user.user_id)})
            except Exception:
                pass
            scope = {"$or": identity_filters}
            return self._merge(scope, extra)

        # Customer / Unknown → deny
        return {"_id": None}

    def branch_filter(self, extra: Optional[dict] = None) -> dict:
        """
        Build a branch query filter.
        """
        if self.is_super_admin:
            return dict(extra or {})

        if self.is_branch_scoped or self.is_delivery:
            scope = {"id": self.user.branch_id}
            return self._merge(scope, extra)

        if self.is_customer:
            # Customers can browse all active branches
            scope = {"status": "active", "is_active": True}
            return self._merge(scope, extra)

        return {"_id": None}

    def user_filter(self, extra: Optional[dict] = None) -> dict:
        """
        Build a user query filter.
        """
        if self.is_super_admin:
            return dict(extra or {})

        if self.is_branch_scoped:
            # Branch managers see staff in their branch
            scope = {"branch_id": self.user.branch_id}
            return self._merge(scope, extra)

        # Everyone else can only see themselves
        from bson.objectid import ObjectId
        identity_filters = [{"user_id": self.user.user_id}]
        try:
            identity_filters.append({"_id": ObjectId(self.user.user_id)})
        except Exception:
            pass
        scope = {"$or": identity_filters}
        return self._merge(scope, extra)

    def menu_filter(self, extra: Optional[dict] = None) -> dict:
        """
        Build a menu item query filter.
        Super admin and branch managers can see all items.
        Others see only active/available items.
        """
        if self.is_super_admin:
            return dict(extra or {})

        if self.is_branch_scoped:
            # Branch-scoped users see their branch's menu
            scope = {}
            if self.user.branch_id:
                scope = {
                    "$or": [
                        {"branch_id": self.user.branch_id},
                        {"branch_id": {"$exists": False}},
                    ]
                }
            return self._merge(scope, extra)

        # Everyone else sees available items only
        scope = {"is_available": True}
        return self._merge(scope, extra)
