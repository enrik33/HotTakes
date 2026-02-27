"""
Health check and status endpoints.
"""

from fastapi import APIRouter
from datetime import datetime
from sqlalchemy import text

router = APIRouter()

# Track app startup time (set in main.py startup)
app_start_time = datetime.utcnow()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.database import SessionLocal

    # Check database connection
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    uptime_seconds = (datetime.utcnow() - app_start_time).total_seconds()

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "1.0.0",
        "uptime_seconds": int(uptime_seconds),
        "timestamp": datetime.utcnow().isoformat(),
        "db_connection": db_status,
        "scheduler_status": "running",
    }
