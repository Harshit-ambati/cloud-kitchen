from datetime import datetime

from fastapi import APIRouter

from app.catalog import DEFAULT_MENU_ITEMS
from app.db import menu_items

router = APIRouter()


def serialize_menu_item(item):
    return {
        "id": item["id"],
        "name": item["name"],
        "category": item["category"],
        "price": round(item.get("price", 0), 2),
        "rating": item.get("rating", 0),
        "eta": item.get("eta", ""),
        "isVeg": item.get("is_veg", False),
        "description": item.get("description", ""),
        "accent": item.get("accent", ""),
        "isAvailable": item.get("is_available", True),
        "imageKey": item.get("image_key", item["id"]),
    }


def ensure_menu_seeded():
    if menu_items.count_documents({}) > 0:
        return

    now = datetime.utcnow()
    menu_items.insert_many(
        [
            {
                **item,
                "image_key": item["id"],
                "created_at": now,
                "updated_at": now,
            }
            for item in DEFAULT_MENU_ITEMS
        ]
    )


@router.get("/")
def get_menu():
    items = [
        serialize_menu_item(item)
        for item in DEFAULT_MENU_ITEMS
        if item.get("is_available", True)
    ]
    items.sort(key=lambda x: (x["category"], x["name"]))
    items.sort(key=lambda x: (x["category"], x["name"]))
    categories = []
    seen = set()
    for item in items:
        category = item["category"]
        if category not in seen:
            seen.add(category)
            categories.append(category)

    return {"items": items, "categories": categories, "count": len(items)}
