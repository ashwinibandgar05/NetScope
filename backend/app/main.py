import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import routes_alerts, routes_history, routes_packets, routes_settings, routes_stats, routes_ws
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.database.session import init_db
from app.services.capture_service import capture_service

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_packets.router, prefix=settings.api_prefix)
app.include_router(routes_stats.router, prefix=settings.api_prefix)
app.include_router(routes_alerts.router, prefix=settings.api_prefix)
app.include_router(routes_history.router, prefix=settings.api_prefix)
app.include_router(routes_settings.router, prefix=settings.api_prefix)
app.include_router(routes_ws.router)


@app.on_event("startup")
async def on_startup():
    init_db()
    logger.info("%s backend started", settings.app_name)
    asyncio.create_task(_sample_throughput_loop())


async def _sample_throughput_loop():
    """Every second, snapshot packets/sec into the rolling history buffer
    used by the live throughput chart."""
    while True:
        await asyncio.sleep(settings.broadcast_interval_seconds)
        capture_service.record_pps_sample()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.app_name}


# Serve the static frontend if present (so `uvicorn app.main:app` alone can
# run the whole thing without a separate frontend dev server).
try:
    app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
except RuntimeError:
    logger.warning("Frontend directory not found — API-only mode")
