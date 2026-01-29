"""Kiro Labyrinth API - Main FastAPI Application."""

import asyncio
import io
import logging
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.api.routes import auth, maze, session, submit, leaderboard
from app.services.submission_service import submission_worker
from app.db.database import async_session_maker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kiro_labyrinth")

settings = get_settings()

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    logger.warning(
        f"Rate limit exceeded for {request.client.host if request.client else 'unknown'} "
        f"on {request.url.path}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "retry_after": str(exc.detail),
        },
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests with correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id

        # Log incoming request
        logger.info(
            f"[{request_id}] --> {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"[{request_id}] <-- {response.status_code} "
                f"({process_time:.2f}ms)"
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] <-- ERROR: {type(e).__name__}: {str(e)} "
                f"({process_time:.2f}ms)"
            )
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Kiro Labyrinth API...")

    # Startup: Seed/update mazes from files
    from app.db.seed import seed_mazes
    async with async_session_maker() as session:
        await seed_mazes(session)
    logger.info("Maze data seeded/updated")

    # Startup: Start submission worker
    worker_task = asyncio.create_task(
        submission_worker(async_session_maker, settings.api_url)
    )
    logger.info("Submission worker started")

    yield

    # Shutdown: Cancel worker
    logger.info("Shutting down Kiro Labyrinth API...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("Submission worker stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Competitive maze-solving challenge platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware - configured based on environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def root() -> dict:
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/config")
async def get_config() -> dict:
    """Get frontend configuration (Google Client ID, etc.)."""
    return {
        "google_client_id": settings.google_client_id if settings.google_client_id else None,
        "debug": settings.debug,
    }


@app.get("/downloads/starter-package.zip")
async def download_starter_package():
    """Download the starter package as a ZIP file."""
    # Check multiple possible locations for starter-package
    possible_paths = [
        Path("/starter-package"),           # Docker compose mount
        Path("/app/starter-package"),       # Railway: copied into backend context
        Path(__file__).parent.parent / "starter-package",  # Relative to app dir
        Path(__file__).parent.parent.parent / "starter-package",  # Project root (local dev)
    ]

    starter_dir = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            starter_dir = path
            logger.info(f"Found starter package at: {starter_dir}")
            break

    if starter_dir is None:
        logger.error(f"Starter package not found. Checked: {[str(p) for p in possible_paths]}")
        raise HTTPException(status_code=404, detail="Starter package not found")

    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in starter_dir.rglob("*"):
            if file_path.is_file():
                # Skip __pycache__ and .pyc files
                if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                    continue
                arcname = file_path.relative_to(starter_dir)
                zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    logger.info(f"Serving starter package ZIP ({zip_buffer.getbuffer().nbytes} bytes)")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=kiro-labyrinth-starter.zip"},
    )


# Include routers
app.include_router(auth.router, prefix="/v1")
app.include_router(maze.router, prefix="/v1")
app.include_router(session.router, prefix="/v1")
app.include_router(submit.router, prefix="/v1")
app.include_router(leaderboard.router, prefix="/v1")
