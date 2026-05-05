"""
Standardised API Response Helpers
-----------------------------------
Frontend-compatible response builders.  Domain data (orders, agents)
stays at top level so existing frontend reads like data.orders work.
The ``status`` field is always present for consistency.
"""

from typing import Any, Optional


def success_response(**kwargs: Any) -> dict:
    """
    Build a success response.  All kwargs become top-level keys.

    Example:
        success_response(orders=[...], count=5)
        → {"status": "success", "orders": [...], "count": 5}
    """
    return {"status": "success", **kwargs}


def error_response(message: str, **kwargs: Any) -> dict:
    """
    Build an error response (non-exception path — e.g. DB-down reads).

    Example:
        error_response("Database unavailable", orders=[], count=0)
        → {"status": "error", "message": "Database unavailable", "orders": [], "count": 0}
    """
    return {"status": "error", "message": message, **kwargs}


def partial_response(message: str, **kwargs: Any) -> dict:
    """
    Build a partial-success response.

    Example:
        partial_response("No valid agents", assignments={})
        → {"status": "partial_success", "message": "No valid agents", "assignments": {}}
    """
    return {"status": "partial_success", "message": message, **kwargs}
