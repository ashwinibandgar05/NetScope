from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])
settings = get_settings()


class RuntimeSettings(BaseModel):
    refresh_rate_ms: int = 1000
    packet_limit: int = 5000
    port_scan_threshold: int = settings.port_scan_threshold
    ping_flood_threshold: int = settings.ping_flood_threshold


_runtime_settings = RuntimeSettings()


@router.get("/", response_model=RuntimeSettings)
async def get_runtime_settings():
    return _runtime_settings


@router.put("/", response_model=RuntimeSettings)
async def update_runtime_settings(payload: RuntimeSettings):
    global _runtime_settings
    _runtime_settings = payload
    settings.port_scan_threshold = payload.port_scan_threshold
    settings.ping_flood_threshold = payload.ping_flood_threshold
    return _runtime_settings
