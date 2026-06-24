"""
Database Configuration
------------------------
MongoDB connection and collection references.
"""

from pymongo import MongoClient
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
)
db = client["cloud_kitchen"]

# ── Collection references ─────────────────────────────────────────────
orders = db["orders"]
agents = db["agents"]
menu_items = db["menu_items"]
users = db["users"]
branches = db["branches"]
