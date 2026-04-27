from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["cloud_kitchen"]

orders = db["orders"]
agents = db["agents"]
menu_items = db["menu_items"]
