"""
Lightweight, in-memory heuristics for flagging suspicious traffic.

Everything here operates on rolling time windows kept per source IP. This
intentionally avoids any external dependency (no rule engine, no ML) —
these are the same kinds of heuristics a junior security tool would use:
count-over-time thresholds per source IP.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Optional

from app.core.config import get_settings

settings = get_settings()


@dataclass
class _IpActivity:
    packet_times: Deque[float] = field(default_factory=deque)
    ports_seen: dict[int, float] = field(default_factory=dict)  # port -> last_seen_ts
    icmp_times: Deque[float] = field(default_factory=deque)
    last_alert_ts: dict[str, float] = field(default_factory=dict)


class DetectionEngine:
    """Stateful engine — one instance lives for the life of the app."""

    ALERT_COOLDOWN_SECONDS = 15  # avoid spamming identical alerts

    def __init__(self):
        self._activity: dict[str, _IpActivity] = defaultdict(_IpActivity)

    def process(self, packet: dict) -> list[dict]:
        """Feed one parsed packet in, get back zero or more alert dicts."""
        alerts: list[dict] = []
        src_ip = packet.get("src_ip")
        if not src_ip:
            return alerts

        now = time.time()
        activity = self._activity[src_ip]

        activity.packet_times.append(now)
        self._trim(activity.packet_times, now, settings.high_volume_window_seconds)

        if packet["protocol"] == "TCP" and packet.get("dst_port"):
            activity.ports_seen[packet["dst_port"]] = now
        if packet["protocol"] == "ICMP":
            activity.icmp_times.append(now)
            self._trim(activity.icmp_times, now, settings.ping_flood_window_seconds)

        alerts += self._check_port_scan(src_ip, activity, now)
        alerts += self._check_ping_flood(src_ip, activity, now)
        alerts += self._check_high_volume(src_ip, activity, now)
        alerts += self._check_suspicious_port(src_ip, packet, activity, now)

        return alerts

    # -- individual heuristics -------------------------------------------------

    def _check_port_scan(self, ip: str, activity: _IpActivity, now: float) -> list[dict]:
        recent_ports = {
            p for p, ts in activity.ports_seen.items()
            if now - ts <= settings.port_scan_window_seconds
        }
        if len(recent_ports) >= settings.port_scan_threshold:
            return self._emit(
                activity, now, "PORT_SCAN",
                f"Source {ip} contacted {len(recent_ports)} distinct ports "
                f"within {settings.port_scan_window_seconds}s",
                severity="high", ip=ip,
            )
        return []

    def _check_ping_flood(self, ip: str, activity: _IpActivity, now: float) -> list[dict]:
        if len(activity.icmp_times) >= settings.ping_flood_threshold:
            return self._emit(
                activity, now, "PING_FLOOD",
                f"Source {ip} sent {len(activity.icmp_times)} ICMP packets "
                f"within {settings.ping_flood_window_seconds}s",
                severity="high", ip=ip,
            )
        return []

    def _check_high_volume(self, ip: str, activity: _IpActivity, now: float) -> list[dict]:
        if len(activity.packet_times) >= settings.high_volume_threshold:
            return self._emit(
                activity, now, "HIGH_VOLUME",
                f"Source {ip} sent {len(activity.packet_times)} packets "
                f"within {settings.high_volume_window_seconds}s",
                severity="medium", ip=ip,
            )
        return []

    def _check_suspicious_port(self, ip: str, packet: dict, activity: _IpActivity, now: float) -> list[dict]:
        dst_port = packet.get("dst_port")
        if dst_port in settings.suspicious_ports:
            return self._emit(
                activity, now, "SUSPICIOUS_PORT",
                f"Source {ip} reached suspicious port {dst_port}",
                severity="medium", ip=ip,
            )
        return []

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _trim(dq: Deque[float], now: float, window: int) -> None:
        while dq and now - dq[0] > window:
            dq.popleft()

    def _emit(self, activity: _IpActivity, now: float, alert_type: str,
              description: str, severity: str, ip: str) -> list[dict]:
        last = activity.last_alert_ts.get(alert_type, 0)
        if now - last < self.ALERT_COOLDOWN_SECONDS:
            return []
        activity.last_alert_ts[alert_type] = now
        return [{
            "alert_type": alert_type,
            "severity": severity,
            "source_ip": ip,
            "description": description,
        }]


detection_engine = DetectionEngine()
