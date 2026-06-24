"""
Backward Compatibility Shim — Branches
-----------------------------------------
Re-exports BRANCHES from the new branch service so existing
imports like `from app.services.branches import BRANCHES`
continue to work.

All branch logic is now in app/services/branch_service.py.
"""

# flake8: noqa: F401
from app.services.branch_service import BRANCHES, STATIC_BRANCHES
