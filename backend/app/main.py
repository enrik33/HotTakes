"""
FastAPI application main entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.routes import health, topics, comments, clusters, timeline
from app.tasks.scheduler import start_scheduler, stop_scheduler

# Create tables on startup
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    # Startup
    if settings.scheduler_enabled:
        start_scheduler()
    yield
    # Shutdown
    if settings.scheduler_enabled:
        stop_scheduler()


app = FastAPI(
    title="HotTakes",
    description="Real-time analysis of Reddit debates",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HotTakes API",
        "docs": "/docs",
        "version": "1.0.0",
    }

