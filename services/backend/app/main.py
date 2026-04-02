"""FastAPI Application with Dependency Injection and Best Practices."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from core.config import get_settings
from core.database import init_database
from core.exception_handlers import setup_exception_handlers
from core.logging import get_logger
from packages.db import close_database
from core.openapi import custom_openapi, OPENAPI_TAGS
from middleware.logging import setup_logging_middleware

# Core routers (always available)
from routers import (
    health,
    users,
    webhooks,
    files,
    buckets,
    agent,
    realtime_agent,
    llm,
    features,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FastAPI Backend...")
    settings = get_settings()

    # Initialize database
    try:
        if settings.database_url:
            logger.info("Initializing database connection...")
            await init_database()
            logger.info("Database initialized successfully")
        else:
            logger.warning("No DATABASE_URL configured - running without database")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Allow app to start without database for development
        if settings.env == "production":
            raise

    # Services are now initialized via dependency injection on first use
    logger.info("Services configured for dependency injection")

    # Log Langfuse status (guarded import)
    try:
        from packages.langfuse import log_status as langfuse_log_status

        langfuse_log_status()
    except ImportError:
        logger.debug("Langfuse package not installed")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI Backend...")
    await close_database()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Full Stack Template API",
        description="Production-ready backend with OpenAI integration, Clerk auth, Neon PostgreSQL, and best practices",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=OPENAPI_TAGS,
    )

    # Middleware
    setup_logging_middleware(app)

    # Exception handlers
    setup_exception_handlers(app)

    # Create API router with /api prefix
    api_router = APIRouter(prefix="/api")

    # ─────────────────────────────────────────────────────────────────────────
    # Core routes (always available)
    # ─────────────────────────────────────────────────────────────────────────
    api_router.include_router(health.router)
    api_router.include_router(features.router)  # /api/features endpoint
    api_router.include_router(users.router, prefix="/users")
    api_router.include_router(webhooks.router, prefix="/webhooks")
    api_router.include_router(llm.router, prefix="/llm")
    api_router.include_router(files.router)
    api_router.include_router(buckets.router)
    api_router.include_router(agent.router, prefix="/agent")
    api_router.include_router(realtime_agent.router, prefix="/realtime")

    # ─────────────────────────────────────────────────────────────────────────
    # Feature: Redis/Jobs (conditional)
    # ─────────────────────────────────────────────────────────────────────────
    if settings.is_redis_enabled:
        try:
            from routers import jobs

            api_router.include_router(jobs.router)
            logger.info("Redis/Jobs routes enabled")
        except ImportError as e:
            logger.warning(f"Redis feature enabled but package not installed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Feature: Temporal/Workflows (conditional)
    # ─────────────────────────────────────────────────────────────────────────
    if settings.is_temporal_enabled:
        try:
            from routers import workflows

            api_router.include_router(workflows.router)
            logger.info("Temporal/Workflows routes enabled")
        except ImportError as e:
            logger.warning(f"Temporal feature enabled but package not installed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Development routes (conditional)
    # ─────────────────────────────────────────────────────────────────────────
    if settings.env == "development":
        from routers import dev_auth

        api_router.include_router(dev_auth.router)
        logger.info("Development routes enabled at /api/dev")

    # Mount the API router
    app.include_router(api_router)

    # Root redirect to docs
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to API documentation."""
        return RedirectResponse(url="/docs")

    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)

    # Log enabled features
    logger.info(
        f"Features: redis={settings.is_redis_enabled}, worker={settings.is_worker_enabled}, temporal={settings.is_temporal_enabled}"
    )

    return app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
