"""
Branch Service
-----------------
CRUD operations and business logic for branch management.
Combines the static BRANCHES list (for backward compat with
the existing branch selector) with a MongoDB-backed branch
collection for the RBAC system.

Migration path:
    Phase 1 (current): Static BRANCHES list + MongoDB branches collection
    Phase 2 (future):  Fully DB-driven, BRANCHES list deprecated
"""

import logging
from datetime import datetime
from typing import List, Optional

from pymongo.errors import PyMongoError

from app.db import db
from app.models.branch import Branch, BranchCreate, BranchUpdate, BranchStatus

logger = logging.getLogger(__name__)

branches_collection = db["branches"]


# ── Static branch data (backward compat with branch_selector) ─────────
# This is the existing data that was in services/branches.py.
# Keep it here so the branch selector and map visualization continue
# to work without changes.

STATIC_BRANCHES = [
    {"id": "b1", "name": "Kukatpally", "lat": 17.4948, "lng": 78.3996},
    {"id": "b2", "name": "HITEC City", "lat": 17.4435, "lng": 78.3772},
    {"id": "b3", "name": "Secunderabad", "lat": 17.4399, "lng": 78.4983},
    {"id": "b4", "name": "LB Nagar", "lat": 17.3457, "lng": 78.5520},
    {"id": "b5", "name": "Mehdipatnam", "lat": 17.3891, "lng": 78.4398},
]

# Re-export for backward compat (services/branches.py used to export BRANCHES)
BRANCHES = STATIC_BRANCHES


def seed_branches_if_empty() -> None:
    """
    Seed the MongoDB branches collection from the static list
    if it's empty.  Called on app startup.
    """
    try:
        if branches_collection.count_documents({}) > 0:
            return

        now = datetime.utcnow()
        docs = []
        for b in STATIC_BRANCHES:
            docs.append({
                "id": b["id"],
                "name": b["name"],
                "address": "",
                "phone": "",
                "lat": b["lat"],
                "lng": b["lng"],
                "status": BranchStatus.ACTIVE.value,
                "service_radius_km": 15.0,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            })
        branches_collection.insert_many(docs)
        logger.info("BRANCHES | Seeded %d branches from static config", len(docs))
    except PyMongoError as exc:
        logger.warning("BRANCHES | Failed to seed branches: %s", exc)


def get_all_branches(active_only: bool = True) -> List[dict]:
    """Return all branches, optionally filtering to active ones only."""
    try:
        query = {"is_active": True} if active_only else {}
        return list(branches_collection.find(query, {"_id": 0}))
    except PyMongoError as exc:
        logger.warning("BRANCHES | DB read failed, falling back to static: %s", exc)
        return STATIC_BRANCHES


def get_branch_by_id(branch_id: str) -> Optional[dict]:
    """Return a single branch by its id field."""
    try:
        branch = branches_collection.find_one({"id": branch_id}, {"_id": 0})
        if branch:
            return branch
    except PyMongoError as exc:
        logger.warning("BRANCHES | DB lookup failed for %s: %s", branch_id, exc)

    # Fallback to static
    return next((b for b in STATIC_BRANCHES if b["id"] == branch_id), None)


def create_branch(data: BranchCreate) -> dict:
    """Create a new branch and return it."""
    now = datetime.utcnow()
    # Generate next branch id
    try:
        last = branches_collection.find_one(sort=[("id", -1)])
        if last and last.get("id", "").startswith("b"):
            next_num = int(last["id"][1:]) + 1
        else:
            next_num = len(STATIC_BRANCHES) + 1
    except (PyMongoError, ValueError):
        next_num = len(STATIC_BRANCHES) + 1

    doc = {
        "id": f"b{next_num}",
        "name": data.name,
        "address": data.address,
        "phone": data.phone,
        "lat": data.lat,
        "lng": data.lng,
        "status": data.status if isinstance(data.status, str) else data.status.value,
        "service_radius_km": data.service_radius_km,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    branches_collection.insert_one(doc)
    doc.pop("_id", None)
    return doc


def update_branch(branch_id: str, data: BranchUpdate) -> Optional[dict]:
    """Update a branch and return the updated document."""
    update_fields = {
        k: v for k, v in data.dict().items()
        if v is not None
    }
    if not update_fields:
        return get_branch_by_id(branch_id)

    update_fields["updated_at"] = datetime.utcnow()

    try:
        branches_collection.update_one(
            {"id": branch_id},
            {"$set": update_fields},
        )
        return get_branch_by_id(branch_id)
    except PyMongoError as exc:
        logger.error("BRANCHES | Update failed for %s: %s", branch_id, exc)
        return None


def delete_branch(branch_id: str) -> bool:
    """Soft-delete a branch by setting is_active = False."""
    try:
        result = branches_collection.update_one(
            {"id": branch_id},
            {"$set": {"is_active": False, "status": BranchStatus.CLOSED.value, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0
    except PyMongoError as exc:
        logger.error("BRANCHES | Delete failed for %s: %s", branch_id, exc)
        return False
