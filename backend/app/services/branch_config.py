"""
Config-Driven Branch Rules
----------------------------
Extends the static BRANCHES list with per-branch configuration.
Branch configs can be overridden via DB (future) or environment.

Each branch has:
    - All fields from BRANCHES (id, name, lat, lng)
    - service_radius_km: maximum delivery distance for this branch
"""

import logging
from typing import Optional

from app.services.branches import BRANCHES

logger = logging.getLogger(__name__)

DEFAULT_SERVICE_RADIUS_KM = 15.0

# ── Per-branch overrides ──────────────────────────────────────────────
# Extend this dict to customise any branch.  Keys not listed here
# fall back to DEFAULT_SERVICE_RADIUS_KM.
_BRANCH_OVERRIDES: dict[str, dict] = {
    # Example: "b2": {"service_radius_km": 12.0},
}


def get_branch_config(branch_id: str) -> dict:
    """
    Return the merged config for a branch: static BRANCHES data +
    any per-branch overrides.
    """
    base = next((b for b in BRANCHES if b["id"] == branch_id), None)
    if base is None:
        return {"service_radius_km": DEFAULT_SERVICE_RADIUS_KM}

    overrides = _BRANCH_OVERRIDES.get(branch_id, {})
    return {
        **base,
        "service_radius_km": overrides.get("service_radius_km", DEFAULT_SERVICE_RADIUS_KM),
    }


def get_service_radius(branch_id: str) -> float:
    """Return the service radius for a specific branch."""
    return get_branch_config(branch_id).get("service_radius_km", DEFAULT_SERVICE_RADIUS_KM)


def get_all_branch_configs() -> list[dict]:
    """Return merged configs for every branch."""
    return [get_branch_config(b["id"]) for b in BRANCHES]
