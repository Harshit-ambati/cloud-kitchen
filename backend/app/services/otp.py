import logging
import random
import re
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.auth.password import hash_password, verify_password
from app.db import db
from app.roles.enums import Role
from app.services.auth import create_user_token

logger = logging.getLogger(__name__)

otp_collection = db["otp_codes"]
users_collection = db["users"]

OTP_TTL_MINUTES = 5


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 8 or len(digits) > 15:
        raise HTTPException(status_code=400, detail="Enter a valid phone number")
    return digits


def request_otp(phone: str) -> dict:
    normalized_phone = normalize_phone(phone)
    code = f"{random.randint(100000, 999999)}"
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)

    otp_collection.update_one(
        {"phone": normalized_phone},
        {
            "$set": {
                "phone": normalized_phone,
                "otp_hash": hash_password(code),
                "expires_at": expires_at,
                "attempts": 0,
                "consumed": False,
                "created_at": now,
            }
        },
        upsert=True,
    )

    logger.info("OTP_REQUESTED | phone=%s otp=%s expires_at=%s", normalized_phone, code, expires_at.isoformat())
    return {
        "message": "OTP sent successfully",
        "phone": normalized_phone,
        "expires_in_minutes": OTP_TTL_MINUTES,
    }


def _get_or_create_customer(phone: str, name: str = "") -> dict:
    user = users_collection.find_one({"phone": phone, "role": Role.CUSTOMER.value})
    now = datetime.utcnow()

    if user:
        updates = {"updated_at": now}
        if name and not user.get("name"):
            updates["name"] = name
        users_collection.update_one({"_id": user["_id"]}, {"$set": updates})
        return users_collection.find_one({"_id": user["_id"]})

    email = f"{phone}@otp.local"
    user = {
        "email": email,
        "password": "",
        "role": Role.CUSTOMER.value,
        "branch_id": None,
        "name": name or "Customer",
        "phone": phone,
        "is_active": True,
        "auth_provider": "otp",
        "created_at": now,
        "updated_at": now,
    }
    result = users_collection.insert_one(user)
    user["_id"] = result.inserted_id
    return user


def verify_otp(phone: str, otp: str, name: str = "") -> dict:
    normalized_phone = normalize_phone(phone)
    record = otp_collection.find_one({"phone": normalized_phone, "consumed": False})

    if not record:
        raise HTTPException(status_code=400, detail="Request a fresh OTP first")
    if record.get("expires_at") < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired. Request a new one")
    if record.get("attempts", 0) >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP")

    if not verify_password(otp, record.get("otp_hash", "")):
        otp_collection.update_one({"_id": record["_id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp_collection.update_one(
        {"_id": record["_id"]},
        {"$set": {"consumed": True, "verified_at": datetime.utcnow()}},
    )
    user = _get_or_create_customer(normalized_phone, name=name)
    return {
        "access_token": create_user_token(user),
        "token_type": "bearer",
        "role": Role.CUSTOMER.value,
        "role_display": Role.CUSTOMER.display_name,
        "user_id": str(user["_id"]),
        "branch_id": None,
        "phone": normalized_phone,
        "name": user.get("name", ""),
    }
