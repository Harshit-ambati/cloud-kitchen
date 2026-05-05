"""End-to-end RBAC test script."""
import requests
import json

BASE = "http://localhost:8000/api"
AUTH_BASE = "http://localhost:8000/auth"

print("=== REGISTERING USERS ===")

# Admin
r = requests.post(f"{AUTH_BASE}/register", json={
    "email": "test_admin",
    "password": "admin123",
    "role": "admin",
    "name": "Test Admin"
})
admin_data = r.json()
print(f"Admin: {r.status_code} - role={admin_data.get('role', admin_data.get('detail'))}")

# Manager (branch b1)
r = requests.post(f"{AUTH_BASE}/register", json={
    "email": "test_manager_b1",
    "password": "mgr123",
    "role": "manager",
    "branch_id": "b1",
    "name": "Kukatpally Manager"
})
mgr_data = r.json()
print(f"Manager: {r.status_code} - role={mgr_data.get('role', mgr_data.get('detail'))} branch={mgr_data.get('branch_id')}")

# Delivery
r = requests.post(f"{AUTH_BASE}/register", json={
    "email": "test_rider",
    "password": "rider123",
    "role": "delivery",
    "name": "Test Rider"
})
rider_data = r.json()
print(f"Delivery: {r.status_code} - role={rider_data.get('role', rider_data.get('detail'))}")

print("\n=== LOGGING IN ===")

r = requests.post(f"{AUTH_BASE}/login", json={"email": "test_admin", "password": "admin123"})
admin_token = r.json().get("access_token")
print(f"Admin login: {r.status_code}, has_token={bool(admin_token)}")

r = requests.post(f"{AUTH_BASE}/login", json={"email": "test_manager_b1", "password": "mgr123"})
manager_token = r.json().get("access_token")
print(f"Manager login: {r.status_code}, has_token={bool(manager_token)}")

r = requests.post(f"{AUTH_BASE}/login", json={"email": "test_rider", "password": "rider123"})
delivery_token = r.json().get("access_token")
print(f"Delivery login: {r.status_code}, has_token={bool(delivery_token)}")

print("\n=== IDENTITY CHECK (/auth/me) ===")
for label, token in [("Admin", admin_token), ("Manager", manager_token), ("Delivery", delivery_token)]:
    r = requests.get(f"{AUTH_BASE}/me", headers={"Authorization": f"Bearer {token}"})
    me = r.json()
    print(f"  {label}: role={me.get('role')}, branch={me.get('branch_id')}, user={me.get('email')}")

print("\n=== ORDER VISIBILITY ===")

# No token (backward compat — behaves like admin)
r = requests.get(f"{BASE}/orders/")
no_token_count = r.json().get("count", 0)
print(f"  No token (admin fallback): {no_token_count} orders")

# Admin
r = requests.get(f"{BASE}/orders/", headers={"Authorization": f"Bearer {admin_token}"})
admin_count = r.json().get("count", 0)
print(f"  Admin: {admin_count} orders")

# Manager (branch b1 only)
r = requests.get(f"{BASE}/orders/", headers={"Authorization": f"Bearer {manager_token}"})
mgr_count = r.json().get("count", 0)
print(f"  Manager (b1): {mgr_count} orders")

# Delivery (only assigned orders)
r = requests.get(f"{BASE}/orders/", headers={"Authorization": f"Bearer {delivery_token}"})
rider_count = r.json().get("count", 0)
print(f"  Delivery: {rider_count} orders")

print("\n=== AGENT VISIBILITY ===")

r = requests.get(f"{BASE}/agents/", headers={"Authorization": f"Bearer {admin_token}"})
admin_agents = len(r.json().get("agents", []))
print(f"  Admin agents: {admin_agents}")

r = requests.get(f"{BASE}/agents/", headers={"Authorization": f"Bearer {delivery_token}"})
rider_agents = len(r.json().get("agents", []))
print(f"  Delivery agents: {rider_agents}")

print("\n=== SECURITY: Delivery cannot run optimize ===")
r = requests.post(f"{BASE}/orders/optimize-assignments", headers={"Authorization": f"Bearer {delivery_token}"})
print(f"  Delivery optimize: {r.status_code} - {r.json().get('detail', 'OK')}")

print("\n=== BACKWARD COMPAT: no-token still works ===")
r = requests.get(f"{BASE}/orders/")
print(f"  No-token orders: status={r.status_code}, count={r.json().get('count', 'error')}")
r = requests.get(f"{BASE}/agents/")
print(f"  No-token agents: status={r.status_code}, count={len(r.json().get('agents', []))}")

print("\n=== FILTERING VERIFICATION ===")
print(f"  Admin sees ALL orders:     {admin_count}")
print(f"  Manager sees BRANCH orders: {mgr_count}")
print(f"  Delivery sees ASSIGNED:     {rider_count}")
if admin_count >= mgr_count >= rider_count:
    print("  Filtering hierarchy: CORRECT (admin >= manager >= delivery)")
else:
    print("  WARNING: unexpected count distribution")

print("\n=== ALL TESTS COMPLETE ===")
