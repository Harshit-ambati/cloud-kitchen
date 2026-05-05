import logging
from app.services.branch_selector import assign_branch
from app.services.branches import BRANCHES

# Setup logging to see the output
logging.basicConfig(level=logging.INFO)

print("--- Testing Branch Assignment (Nearest Branch Logic) ---")

locations = [
    {"name": "North-West Hyderabad", "lat": 17.5100, "lng": 78.3800},
    {"name": "South-East Hyderabad", "lat": 17.3400, "lng": 78.5600},
    {"name": "Central Hyderabad", "lat": 17.4000, "lng": 78.4800},
    {"name": "Outside All Branches (>10km)", "lat": 17.0000, "lng": 78.0000}
]

for loc in locations:
    print(f"\nSimulating order from {loc['name']} ({loc['lat']}, {loc['lng']})")
    branch, dist = assign_branch(loc["lat"], loc["lng"])
    print(f"-> Assigned Branch: {branch['name']} (Distance: {dist:.2f} km)")

print("\nAll tests completed.")
