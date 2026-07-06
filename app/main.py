"""
TheMemeCanvas Automation Suite — FastAPI Application Entry Point
================================================================
Initializes the FastAPI app, registers routers, configures CORS,
and manages the scheduler lifecycle via lifespan events.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.database.base import init_db
from app.dashboard.router import router as dashboard_router
from app.utils.logging_setup import setup_logging

logger = logging.getLogger("thememecanvas")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan — runs on startup and shutdown.
    Handles database initialization, scheduler start, and cleanup.
    """
    # === STARTUP ===
    logger.info("=" * 60)
    logger.info("  TheMemeCanvas Automation Suite — Starting Up")
    logger.info("  Environment: %s", settings.app_env)
    logger.info("  Upload Time: %s %s", settings.upload_time, settings.timezone)
    logger.info("=" * 60)

    # Initialize database tables
    try:
        init_db()
        logger.info("✅ Database initialized.")
    except Exception as e:
        logger.error("❌ Database initialization failed: %s", e)

    # Ensure required directories exist
    for directory in [
        "logs", "temp_downloads", "temp_thumbnails",
        "assets", "credentials", "data"
    ]:
        Path(directory).mkdir(parents=True, exist_ok=True)

    # Generate default thumbnail if missing
    try:
        if not settings.default_thumbnail_path.exists():
            from app.services.thumbnail.default import create_default_thumbnail
            create_default_thumbnail()
            logger.info("✅ Default thumbnail created.")
    except Exception as e:
        logger.warning("Could not create default thumbnail: %s", e)

    # Start scheduler
    try:
        from app.scheduler.runner import init_scheduler, start_scheduler
        init_scheduler()
        start_scheduler()
        logger.info("✅ Scheduler started.")
    except Exception as e:
        logger.error("❌ Scheduler failed to start: %s", e)

    logger.info("✅ Application startup complete.")
    logger.info("📊 Dashboard: http://%s:%d", settings.app_host, settings.app_port)

    yield  # Application is running

    # === SHUTDOWN ===
    logger.info("Shutting down TheMemeCanvas Automation Suite...")
    try:
        from app.scheduler.runner import stop_scheduler
        stop_scheduler()
        logger.info("Scheduler stopped.")
    except Exception as e:
        logger.warning("Scheduler stop error: %s", e)

    logger.info("Goodbye! 🎭")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Setup logging first
    setup_logging()

    app = FastAPI(
        title="TheMemeCanvas Automation Suite",
        description="Production-grade content distribution platform for YouTube Shorts & Instagram Reels",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],  # React dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- API Routes ---
    app.include_router(dashboard_router)

    # --- Serve React Frontend (built files) ---
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            """Serve React app for all non-API routes."""
            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"message": "Frontend not built. Run 'npm run build' in the frontend/ directory."}

    # --- Root redirect ---
    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/api/docs")

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
