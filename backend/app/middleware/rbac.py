"""
RBAC Middleware
-----------------
Permission-based route guards using FastAPI's dependency injection.

Usage in routes:
    from app.middleware import require_permissions
    from app.roles import Permission

    @router.get("/")
    def list_orders(
        user = Depends(require_permissions(Permission.ORDERS_READ))
    ):
        ...

The require_permissions dependency:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes and validates the JWT
    3. Looks up the user in the database (with JWT fallback)
    4. Checks that the user's role grants ALL required permissions
    5. Returns the CurrentUser object for use in the route handler

Future extension points:
    - Resource-level permission checks (e.g. "can this user edit THIS order?")
    - Rate limiting per role
    - Audit logging
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.dependencies.auth import CurrentUser, get_current_user
from app.roles.enums import Permission, Role
from app.roles.permissions import has_permission, has_any_permission

logger = logging.getLogger(__name__)


class RBACMiddleware:
    """
    Callable dependency that checks if the current user has ALL
    of the required permissions.

    Usage:
        rbac = RBACMiddleware(Permission.ORDERS_READ, Permission.ORDERS_ASSIGN)

        @router.post("/assign")
        def assign(user: CurrentUser = Depends(rbac)):
            ...
    """

    def __init__(self, *required_permissions: Permission):
        self.required_permissions = required_permissions

    async def __call__(
        self, request: Request, current_user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        # Check active status
        if not current_user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Account is deactivated. Contact support.",
            )

        # Check each required permission
        missing = [
            perm.value
            for perm in self.required_permissions
            if not has_permission(current_user.role, perm)
        ]
        if missing:
            logger.warning(
                "RBAC_DENY | user=%s role=%s missing_permissions=%s path=%s",
                current_user.user_id,
                current_user.role,
                missing,
                request.url.path,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Missing: {', '.join(missing)}",
            )

        return current_user


def require_permissions(*permissions: Permission):
    """
    Convenience factory that returns a FastAPI dependency requiring ALL permissions.

    Usage:
        @router.get("/", dependencies=[Depends(require_permissions(Permission.ORDERS_READ))])
        def list_orders():
            ...

    Or, to get the user object:
        @router.get("/")
        def list_orders(user = Depends(require_permissions(Permission.ORDERS_READ))):
            ...
    """
    checker = RBACMiddleware(*permissions)

    async def dependency(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        return await checker(request, current_user)

    return dependency


def require_any_permission(*permissions: Permission):
    """
    Convenience factory that returns a FastAPI dependency requiring ANY ONE
    of the given permissions.

    Usage:
        @router.get("/")
        def list_orders(user = Depends(require_any_permission(
            Permission.ORDERS_READ, Permission.ORDERS_READ_OWN
        ))):
            ...
    """

    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        if not has_any_permission(current_user.role, *permissions):
            logger.warning(
                "RBAC_DENY | user=%s role=%s requires_any=%s",
                current_user.user_id,
                current_user.role,
                [p.value for p in permissions],
            )
            raise HTTPException(
                status_code=403,
                detail=f"Requires at least one of: {', '.join(p.value for p in permissions)}",
            )

        return current_user

    return dependency


def require_role(*roles: str):
    """
    Convenience factory that restricts access to specific roles.
    Supports both new Role enum values and legacy strings.

    Usage:
        @router.get("/admin-only")
        def admin_panel(user = Depends(require_role(Role.SUPER_ADMIN))):
            ...
    """
    async def dependency(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        # Normalize both sides for comparison
        try:
            user_role = Role.normalize(current_user.role)
        except ValueError:
            raise HTTPException(status_code=403, detail=f"Unknown role: {current_user.role}")

        allowed = set()
        for r in roles:
            try:
                allowed.add(Role.normalize(r) if isinstance(r, str) else r)
            except ValueError:
                continue

        # SUPER_ADMIN always passes role checks
        if user_role == Role.SUPER_ADMIN:
            return current_user

        if user_role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Access requires one of: {', '.join(r.value for r in allowed)}",
            )

        return current_user

    return dependency


def require_branch_access(branch_id_param: str = "branch_id"):
    """
    Ensure the current user has access to the branch specified
    in the path/query parameter.

    SUPER_ADMIN: unrestricted
    Branch-scoped roles: must match their assigned branch_id
    """

    async def dependency(
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        try:
            user_role = Role.normalize(current_user.role)
        except ValueError:
            raise HTTPException(status_code=403, detail=f"Unknown role: {current_user.role}")

        # Super admin can access any branch
        if user_role == Role.SUPER_ADMIN:
            return current_user

        # Extract branch_id from path params or query params
        target_branch_id = request.path_params.get(branch_id_param)
        if not target_branch_id:
            target_branch_id = request.query_params.get(branch_id_param)

        if target_branch_id and current_user.branch_id != target_branch_id:
            logger.warning(
                "BRANCH_DENY | user=%s branch=%s tried to access branch=%s",
                current_user.user_id,
                current_user.branch_id,
                target_branch_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: you can only access your assigned branch",
            )

        return current_user

    return dependency
