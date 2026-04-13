"""
TracePilot API -- FastAPI entry point.
Configures middleware, startup tasks, and route includes.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

# ── Request size limit middleware ────────────────────────────────────────────

MAX_REQUEST_BYTES = settings.MAX_REQUEST_SIZE_MB * 1024 * 1024


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Reject requests whose Content-Length exceeds the configured limit."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={"detail": f"Request body exceeds {settings.MAX_REQUEST_SIZE_MB}MB limit"},
        )
    return await call_next(request)


# ── CORS (environment-variable-based) ───────────────────────────────────────

_origins = (
    ["*"]
    if settings.CORS_ORIGINS.strip() == "*"
    else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
