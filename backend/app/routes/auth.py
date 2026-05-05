import logging
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from pymongo.errors import PyMongoError

from app.dependencies.auth import UserLogin, users_collection, get_current_user, CurrentUser
from app.services.auth import authenticate_user, create_user_token, hash_password
from app.auth import UserRegister

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister):
    try:
        if users_collection.find_one({"email": payload.email}):
            raise HTTPException(status_code=400, detail="User with this email already exists")

        new_user = {
            "email": payload.email,
            "password": hash_password(payload.password),
            "role": payload.role,
            "branch_id": payload.branch_id,
            "name": payload.name,
            "created_at": datetime.utcnow()
        }
        
        result = users_collection.insert_one(new_user)
        return {"message": "User registered successfully", "user_id": str(result.inserted_id)}
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | register failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.post("/login")
def login(payload: UserLogin):
    try:
        user = authenticate_user(payload.email, payload.password)
        return {
            "access_token": create_user_token(user),
            "token_type": "bearer",
            "role": user.get("role"),
            "user_id": str(user["_id"])
        }
    except HTTPException:
        raise
    except PyMongoError as exc:
        logger.error("DB_ERROR | login failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Please try again.",
        )


@router.get("/me")
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user.dict()
