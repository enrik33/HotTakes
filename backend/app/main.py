"""
FastAPI application main entry point.
"""

from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.errors import STATUS_CODE_DEFAULTS, build_error_payload
from app.logging_config import REQUEST_ID_CTX, get_logger, setup_logging
from app.routes import clusters, comments, health, timeline, topics
from app.tasks.scheduler import start_scheduler, stop_scheduler

import time

setup_logging(settings.log_level)
logger = get_logger(__name__, component="api")


def _init_db(retries: int = 10, delay: float = 3.0) -> None:
    """Create tables, retrying if the DB isn't ready yet."""
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info(
                "db_init_ok",
                extra={"event": "db_init_ok", "component": "api", "request_id": "-"},
            )
            return
        except Exception as exc:
            logger.warning(
                "db_init_retry",
                extra={
                    "event": "db_init_retry",
                    "component": "api",
                    "request_id": "-",
                    "attempt": attempt,
                    "error": str(exc),
                },
            )
            if attempt == retries:
                raise
            time.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    logger.info(
        "api_startup",
        extra={"event": "api_startup", "component": "api", "request_id": "-"},
    )
    _init_db()
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    if settings.scheduler_enabled:
        stop_scheduler()
    logger.info(
        "api_shutdown",
        extra={"event": "api_shutdown", "component": "api", "request_id": "-"},
    )


app = FastAPI(
    title="HotTakes",
    description="Real-time analysis of Hacker News tech discourse",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(topics.router, prefix="/api", tags=["topics"])
app.include_router(comments.router, prefix="/api", tags=["comments"])
app.include_router(clusters.router, prefix="/api", tags=["clusters"])
app.include_router(timeline.router, prefix="/api", tags=["timeline"])


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Attach request ID and log request lifecycle."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    token = REQUEST_ID_CTX.set(request_id)
    start = perf_counter()

    logger.info(
        "request_started",
        extra={
            "event": "request_started",
            "component": "api",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "component": "api",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    except Exception:
        duration_ms = round((perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "event": "request_failed",
                "component": "api",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    finally:
        REQUEST_ID_CTX.reset(token)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected exceptions with stack trace."""
    request_id = request.headers.get("X-Request-ID", REQUEST_ID_CTX.get())
    logger.exception(
        "unhandled_exception",
        extra={
            "event": "unhandled_exception",
            "component": "api",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )
    return JSONResponse(
        status_code=500,
        content=build_error_payload(
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
            details=None,
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Normalize HTTPException responses to standard error schema."""
    request_id = request.headers.get("X-Request-ID", REQUEST_ID_CTX.get())
    details = None
    code = STATUS_CODE_DEFAULTS.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.detail else "HTTP error"

    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", code)
        message = exc.detail.get("message", message)
        details = exc.detail.get("details")

    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Normalize validation errors to standard error schema."""
    request_id = request.headers.get("X-Request-ID", REQUEST_ID_CTX.get())
    return JSONResponse(
        status_code=422,
        content=build_error_payload(
            code="VALIDATION_ERROR",
            message="Validation error",
            details=exc.errors(),
            request_id=request_id,
        ),
        headers={"X-Request-ID": request_id},
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "HotTakes API", "docs": "/docs", "version": "2.0.0"}
