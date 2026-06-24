"""
Backward Compatibility Shim — Policy
--------------------------------------
Re-exports from new app/permissions/ modules so existing imports work.
"""

from app.permissions.role_guards import (
    resolve_role,
    is_delivery_role,
    is_kitchen_staff,
    is_customer,
    is_admin,
    is_manager,
    enforce_admin_only,
    enforce_admin_or_manager,
)
from app.permissions.ownership import enforce_ownership
from app.permissions.branch_scope import enforce_branch_match
from app.permissions.delivery_scope import (
    enforce_not_delivery,
    filter_agent_update,
    enforce_delivery_status_permission,
)
from app.permissions.kitchen_scope import (
    enforce_kitchen_or_above,
    enforce_kitchen_status_permission,
)

# A combined helper for the orders route backwards compatibility
def enforce_status_permission_combined(current_user, new_status: str) -> None:
    enforce_delivery_status_permission(current_user, new_status)
    enforce_kitchen_status_permission(current_user, new_status)

# Shim for the old combined function
enforce_delivery_status_permission = enforce_status_permission_combined
