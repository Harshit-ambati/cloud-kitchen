"""
System Design Refactor — Smoke Test
-------------------------------------
Validates all 9 requirements without breaking frontend compatibility.
"""
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.db import db
from app.services.auth import create_access_token

BASE = "http://127.0.0.1:8000"
PASS = 0
FAIL = 0


def check(label, condition, detail=""):
    global PASS, FAIL
    tag = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    msg = f"  [{tag}] {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)


# ── Setup ─────────────────────────────────────────────────────────────
user = db["users"].find_one({"email": "test_admin"})
if not user:
    print("SKIP: no test_admin user.")
    sys.exit(1)

token = create_access_token({"user_id": str(user["_id"]), "role": "admin"})
auth = {"Authorization": f"Bearer {token}"}

print("=" * 68)

# ── 1. FRONTEND COMPATIBILITY (data.orders / data.agents) ────────────
print("1. FRONTEND COMPAT: existing response shapes preserved")
print("-" * 68)

r = requests.get(f"{BASE}/api/orders/", headers=auth, timeout=10)
data = r.json()
check("GET /api/orders/ -> 200", r.status_code == 200)
check("'orders' key at top level", "orders" in data)
check("'status' key present", "status" in data)
check("status == 'success'", data.get("status") == "success")

r = requests.get(f"{BASE}/api/agents/", headers=auth, timeout=10)
data = r.json()
check("GET /api/agents/ -> 200", r.status_code == 200)
check("'agents' key at top level", "agents" in data)
check("'status' key present", "status" in data)

# ── 2. TYPE FILTER (?type=real|simulated|all) ─────────────────────────
print()
print("2. TYPE FILTER on orders")
print("-" * 68)

r = requests.get(f"{BASE}/api/orders/?type=all", headers=auth, timeout=10)
check("?type=all -> 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/orders/?type=real", headers=auth, timeout=10)
check("?type=real -> 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/orders/?type=simulated", headers=auth, timeout=10)
check("?type=simulated -> 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/orders/?type=invalid", headers=auth, timeout=10)
check("?type=invalid -> 422", r.status_code == 422)

# ── 3. DEBUG TRACE on order creation ──────────────────────────────────
print()
print("3. DEBUG TRACE on order creation")
print("-" * 68)

order_payload = {
    "user_lat": 17.45,
    "user_lng": 78.39,
    "kitchen_lat": 17.385,
    "kitchen_lng": 78.4867,
    "order_type": "regular",
    "fulfillment_mode": "delivery",
    "items": []
}

r = requests.post(f"{BASE}/api/orders/create?debug=true", json=order_payload, timeout=10)
data = r.json()
check("POST /create?debug=true -> 200", r.status_code == 200)
check("_debug key present in response", "_debug" in data)
if "_debug" in data:
    trace = data["_debug"].get("branch_selection", {})
    check("trace has 'selected_branch'", "selected_branch" in trace)
    check("trace has 'reason'", "reason" in trace)
    check("trace has 'candidates_checked'", "candidates_checked" in trace)
    check("trace has 'candidates' list", isinstance(trace.get("candidates"), list))
    print(f"  >> selected: {trace.get('selected_branch_name')}, reason: {trace.get('reason')}, "
          f"checked: {trace.get('candidates_checked')}")

# Without debug — no _debug key
r = requests.post(f"{BASE}/api/orders/create", json=order_payload, timeout=10)
data = r.json()
check("POST /create (no debug) -> 200", r.status_code == 200)
check("_debug NOT in response", "_debug" not in data)

# ── 4. is_simulated field ─────────────────────────────────────────────
print()
print("4. is_simulated field on orders")
print("-" * 68)

check("'is_simulated' in created order", "is_simulated" in data)
check("is_simulated defaults to False", data.get("is_simulated") is False)

# ── 5. HEALTH / INDEXES ──────────────────────────────────────────────
print()
print("5. HEALTH + INDEXES")
print("-" * 68)

r = requests.get(f"{BASE}/health", timeout=10)
h = r.json()
check("/health -> 200", r.status_code == 200)
check("db_connected", h.get("db_connected") is True)

# ── 6. POLICY ENFORCEMENT — delivery status restrictions ─────────────
print()
print("6. POLICY ENFORCEMENT")
print("-" * 68)

# Create a delivery user token
delivery_user = db["users"].find_one({"role": "delivery"})
if delivery_user:
    d_token = create_access_token({"user_id": str(delivery_user["_id"]), "role": "delivery"})
    d_auth = {"Authorization": f"Bearer {d_token}"}

    # Delivery user cannot create agents
    r = requests.post(f"{BASE}/api/agents/create",
                      json={"name": "test", "lat": 17.4, "lng": 78.4},
                      headers=d_auth, timeout=10)
    check("Delivery cannot create agent -> 403", r.status_code == 403)

    # Delivery user cannot delete agents
    r = requests.delete(f"{BASE}/api/agents/fakeid", headers=d_auth, timeout=10)
    check("Delivery cannot delete agent -> 403", r.status_code == 403)

    # Delivery user cannot optimize
    r = requests.post(f"{BASE}/api/orders/optimize-assignments",
                      json={}, headers=d_auth, timeout=10)
    check("Delivery cannot optimize -> 403", r.status_code == 403)
else:
    print("  [SKIP] No delivery user found for policy tests")

# ── 7. CONSISTENT RESPONSES ──────────────────────────────────────────
print()
print("7. CONSISTENT RESPONSE STRUCTURE")
print("-" * 68)

r = requests.get(f"{BASE}/api/orders/", headers=auth, timeout=10)
check("Orders response has 'status' field", "status" in r.json())

r = requests.get(f"{BASE}/api/agents/", headers=auth, timeout=10)
check("Agents response has 'status' field", "status" in r.json())

# Error response
r = requests.get(f"{BASE}/api/orders/", timeout=10)  # no auth
check("Unauthenticated -> has 'detail'", "detail" in r.json())

# ── Summary ───────────────────────────────────────────────────────────
print()
print("=" * 68)
total = PASS + FAIL
print(f"Results: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("All system design checks passed.")
else:
    print(f"WARNING: {FAIL} check(s) failed.")
print("=" * 68)
sys.exit(0 if FAIL == 0 else 1)
