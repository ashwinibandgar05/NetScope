from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import stats_service
from app.services.capture_service import capture_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
async def dashboard_stats():
    """Live in-memory counters — used for the top dashboard cards."""
    return capture_service.current_stats()


@router.get("/throughput")
async def throughput_history():
    """Rolling packets/sec samples for the real-time line chart."""
    return {"points": capture_service.pps_history()}


@router.get("/traffic")
async def traffic_stats(db: Session = Depends(get_db)):
    """Historical breakdown pulled from SQLite — protocol mix, top talkers, ports."""
    return stats_service.traffic_stats(db)
