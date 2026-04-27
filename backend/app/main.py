import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.orders import router as orders_router
from app.routes.agents import router as agents_router
from app.routes.menu import router as menu_router

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

@app.get("/")
def home():
    return {"message": "Cloud Kitchen API 🚀", "version": "1.0.0"}
