import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

from app.config import settings
from app.routes.orders import router as orders_router
from app.routes.agents import router as agents_router
from app.routes.menu import router as menu_router
from app.routes.auth import router as auth_router
from app.routes.branches import router as branches_router
from app.routes.users import router as users_router
from app.routes.internal import router as internal_router
from app.routes.health import router as health_router
from app.middleware.request_context import RequestContextMiddleware, SecurityHeadersMiddleware

# ── Logging configuration ─────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-branch cloud kitchen platform with RBAC",
)

# ── Middleware stack (order matters — outermost first) ─────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Route registration ───────────────────────────────────────────────
app.include_router(orders_router, prefix="/api/orders", tags=["Orders"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(menu_router, prefix="/api/menu", tags=["Menu"])
app.include_router(branches_router, prefix="/api/branches", tags=["Branches"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(internal_router, prefix="/internal", tags=["Internal"])
app.include_router(health_router, tags=["Health"])


# ── Startup: ensure database indexes + seed branches ────────────────
@app.on_event("startup")
def on_startup():
    from app.services.indexes import ensure_indexes
    from app.services.branch_service import seed_branches_if_empty

    ensure_indexes()
    seed_branches_if_empty()
    logger.info("APP_STARTUP | %s v%s ready", settings.APP_NAME, settings.APP_VERSION)


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
    from app.roles.enums import Role
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "rbac": "multi-branch",
        "roles": [r.value for r in Role.all_canonical()],
        "endpoints": {
            "auth": "/auth",
            "orders": "/api/orders",
            "agents": "/api/agents",
            "menu": "/api/menu",
            "branches": "/api/branches",
            "users": "/api/users",
            "health": "/health",
        },
    }
