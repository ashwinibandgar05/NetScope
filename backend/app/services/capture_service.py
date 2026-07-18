"""
Orchestrates the moving parts of a capture session:

  sniffer thread -> parsed packet -> in-memory ring buffer
                                   -> persisted to SQLite
                                   -> fed to the detection engine
                                   -> broadcast to WebSocket clients

This is the single place that ties capture, storage, detection and
real-time delivery together, so API routes stay thin.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Deque, Optional

from app.api.websocket import connection_manager
from app.capture.sniffer import PacketSniffer
from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.alert import Alert
from app.models.packet import Packet
from app.models.session import CaptureSession
from app.services.detection_service import detection_engine

logger = logging.getLogger(__name__)
settings = get_settings()


class CaptureService:
    """Singleton-style service (one instance per process) that owns
    capture state. Instantiated once in main.py and shared across routes
    via FastAPI dependency injection."""

    def __init__(self):
        self._sniffer: Optional[PacketSniffer] = None
        self._current_session_id: Optional[int] = None
        self._interface: Optional[str] = None

        self._buffer: Deque[dict] = deque(maxlen=settings.max_packets_in_memory)
        self._packet_time_window: Deque[float] = deque()
        self._byte_window: Deque[tuple[float, int]] = deque()
        self._protocol_totals: dict[str, int] = {"TCP": 0, "UDP": 0, "ICMP": 0, "ARP": 0, "OTHER": 0}
        self._total_packets = 0
        self._pps_history: Deque[dict] = deque(maxlen=60)  # last 60 samples for the line chart

    # -- lifecycle -------------------------------------------------------

    def is_running(self) -> bool:
        return self._sniffer is not None and self._sniffer.is_running()

    def start(self, loop: asyncio.AbstractEventLoop, interface: Optional[str] = None) -> int:
        if self.is_running():
            return self._current_session_id  # type: ignore[return-value]

        self._interface = interface
        db = SessionLocal()
        try:
            session = CaptureSession(interface=interface, status="running")
            db.add(session)
            db.commit()
            db.refresh(session)
            self._current_session_id = session.id
        finally:
            db.close()

        self._sniffer = PacketSniffer(on_packet=self._on_packet_sync, interface=interface)
        self._sniffer.start(loop)
        return self._current_session_id

    def stop(self) -> None:
        if self._sniffer:
            self._sniffer.stop()

        if self._current_session_id is not None:
            db = SessionLocal()
            try:
                session = db.query(CaptureSession).get(self._current_session_id)
                if session:
                    session.status = "stopped"
                    session.ended_at = datetime.utcnow()
                    session.total_packets = self._total_packets
                    db.commit()
            finally:
                db.close()
        self._current_session_id = None

    # -- ingestion ---------------------------------------------------------

    def _on_packet_sync(self, packet: dict) -> None:
        """Runs on the asyncio loop (scheduled via call_soon_threadsafe)."""
        asyncio.create_task(self._handle_packet(packet))

    async def _handle_packet(self, packet: dict) -> None:
        now = time.time()
        packet["timestamp"] = datetime.utcnow()
        packet["session_id"] = self._current_session_id

        self._buffer.append(packet)
        self._total_packets += 1
        proto = packet.get("protocol", "OTHER")
        self._protocol_totals[proto] = self._protocol_totals.get(proto, 0) + 1

        self._packet_time_window.append(now)
        self._byte_window.append((now, packet.get("length", 0)))
        self._trim_windows(now)

        self._persist(packet)

        alerts = detection_engine.process(packet)
        for alert in alerts:
            self._persist_alert(alert)
            await connection_manager.broadcast({"type": "alert", "data": alert})

        await connection_manager.broadcast({"type": "packet", "data": self._serialize(packet)})

    def _trim_windows(self, now: float, window_seconds: int = 10) -> None:
        while self._packet_time_window and now - self._packet_time_window[0] > window_seconds:
            self._packet_time_window.popleft()
        while self._byte_window and now - self._byte_window[0][0] > window_seconds:
            self._byte_window.popleft()

    def _persist(self, packet: dict) -> None:
        db = SessionLocal()
        try:
            row = Packet(
                session_id=packet.get("session_id"),
                timestamp=packet["timestamp"],
                src_ip=packet.get("src_ip", ""),
                dst_ip=packet.get("dst_ip", ""),
                src_port=packet.get("src_port"),
                dst_port=packet.get("dst_port"),
                protocol=packet.get("protocol", "OTHER"),
                app_protocol=packet.get("app_protocol"),
                length=packet.get("length", 0),
                ttl=packet.get("ttl"),
                flags=packet.get("flags"),
                raw_summary=packet.get("raw_summary"),
            )
            db.add(row)
            db.commit()
        except Exception:
            logger.exception("Failed to persist packet")
            db.rollback()
        finally:
            db.close()

    def _persist_alert(self, alert: dict) -> None:
        db = SessionLocal()
        try:
            row = Alert(**alert)
            db.add(row)
            db.commit()
        except Exception:
            logger.exception("Failed to persist alert")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def _serialize(packet: dict) -> dict:
        out = dict(packet)
        out["timestamp"] = out["timestamp"].isoformat() if isinstance(out.get("timestamp"), datetime) else out.get("timestamp")
        return out

    # -- read access for API layer -----------------------------------------

    def recent_packets(self, limit: int = 200) -> list[dict]:
        items = list(self._buffer)[-limit:]
        return [self._serialize(p) for p in reversed(items)]

    def current_stats(self) -> dict:
        pps = len(self._packet_time_window) / 10.0
        bps = sum(size for _, size in self._byte_window) / 10.0
        return {
            "total_packets": self._total_packets,
            "tcp_packets": self._protocol_totals.get("TCP", 0),
            "udp_packets": self._protocol_totals.get("UDP", 0),
            "icmp_packets": self._protocol_totals.get("ICMP", 0),
            "unknown_packets": self._protocol_totals.get("OTHER", 0) + self._protocol_totals.get("ARP", 0),
            "packets_per_second": round(pps, 2),
            "bandwidth_bytes_per_second": round(bps, 2),
        }

    def record_pps_sample(self) -> None:
        stats = self.current_stats()
        self._pps_history.append({
            "label": datetime.utcnow().strftime("%H:%M:%S"),
            "value": stats["packets_per_second"],
        })

    def pps_history(self) -> list[dict]:
        return list(self._pps_history)

    @property
    def active_session_id(self) -> Optional[int]:
        return self._current_session_id

    @property
    def interface(self) -> Optional[str]:
        return self._interface


capture_service = CaptureService()
