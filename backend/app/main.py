import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from app.routes.orders import router as orders_router
from app.routes.agents import router as agents_router
from app.routes.menu import router as menu_router
from app.routes.auth import router as auth_router
from app.routes.internal import router as internal_router
from app.routes.health import router as health_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Cloud Kitchen API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(menu_router, prefix="/api/menu", tags=["Menu"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(internal_router, prefix="/internal", tags=["Internal"])
app.include_router(health_router, tags=["Health"])


# ── Startup: ensure database indexes ────────────────────────────────────
@app.on_event("startup")
def on_startup():
    from app.services.indexes import ensure_indexes
    ensure_indexes()


# ── Global exception safety net ─────────────────────────────────────────
# These catch any PyMongo errors that slip past route-level try/except
# blocks, ensuring raw stack traces never reach the client.

@app.exception_handler(ServerSelectionTimeoutError)
async def mongo_connection_exception_handler(request: Request, exc: ServerSelectionTimeoutError):
    logger.error("GLOBAL_HANDLER | ServerSelectionTimeoutError on %s %s: %s",
                 request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "message": "Service temporarily unavailable. Please try again.",
            "detail": "Database connection timed out.",
        },
    )


@app.exception_handler(PyMongoError)
async def pymongo_exception_handler(request: Request, exc: PyMongoError):
    logger.error("GLOBAL_HANDLER | PyMongoError on %s %s: %s",
                 request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "message": "Service temporarily unavailable. Please try again.",
            "detail": "Database operation failed.",
        },
    )


@app.get("/")
def home():
    return {"message": "Cloud Kitchen API", "version": "1.0.0"}
