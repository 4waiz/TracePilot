"""
TracePilot API -- FastAPI entry point.
Configures middleware, startup tasks, and route includes.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.seed import run_seed


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run setup tasks before the app starts accepting requests."""
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)

    # Create tables and seed demo users
    run_seed()

    yield  # App is running

    # Shutdown tasks (if any) go here


# ── App creation ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="TracePilot API",
    description="AI-powered inspection and traceability platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (permissive for development) ────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving for uploads ──────────────────────────────────────────

# Mount after startup so the directory is guaranteed to exist
@app.on_event("startup")
async def mount_static():
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Routers ──────────────────────────────────────────────────────────────────

from backend.routers import (
    auth_routes,
    job_routes,
    document_routes,
    extraction_routes,
    inspection_routes,
    deviation_routes,
    report_routes,
    audit_routes,
)

app.include_router(auth_routes.router)
app.include_router(job_routes.router)
app.include_router(document_routes.router)
app.include_router(extraction_routes.router)
app.include_router(inspection_routes.router)
app.include_router(deviation_routes.router)
app.include_router(report_routes.router)
app.include_router(audit_routes.router)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """Simple health probe for load balancers and monitoring."""
    return {"status": "ok", "service": "TracePilot API"}
