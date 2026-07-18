"""
Scapy's sniff() is blocking and synchronous, so it can't run directly on
the asyncio event loop FastAPI uses. We run it in a dedicated background
thread and hand parsed packets back to the async world via a thread-safe
callback that schedules work on the main loop.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Callable, Optional

from scapy.all import sniff, get_if_list

from app.capture.parser import parse_packet

logger = logging.getLogger(__name__)

PacketHandler = Callable[[dict], None]


class PacketSniffer:
    """Wraps scapy.sniff in a background thread with start/stop control."""

    def __init__(self, on_packet: PacketHandler, interface: Optional[str] = None):
        self._on_packet = on_packet
        self._interface = interface
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @staticmethod
    def list_interfaces() -> list[str]:
        try:
            return get_if_list()
        except Exception as exc:  # pragma: no cover - platform dependent
            logger.warning("Could not list interfaces: %s", exc)
            return []

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        if self.is_running():
            logger.info("Sniffer already running, ignoring start()")
            return

        self._loop = loop
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="netscope-sniffer")
        self._thread.start()
        logger.info("Packet sniffer started on interface=%s", self._interface or "default")

    def stop(self) -> None:
        self._stop_event.set()
        self._thread = None
        logger.info("Packet sniffer stop requested")

    def _run(self) -> None:
        def _stop_filter(_pkt) -> bool:
            return self._stop_event.is_set()

        def _handle(pkt) -> None:
            parsed = parse_packet(pkt)
            if parsed is None:
                return
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._on_packet, parsed)

        try:
            self._sniff_with_fallback(_handle, _stop_filter)
        except PermissionError:
            logger.error(
                "Packet capture requires elevated privileges. "
                "Run the backend with sudo/administrator rights."
            )
        except Exception as exc:  # pragma: no cover - hardware/OS dependent
            logger.exception("Sniffer crashed: %s", exc)

    def _sniff_with_fallback(self, handler, stop_filter) -> None:
        """Try the requested interface; if libpcap can't open it (common on
        Windows when a raw adapter GUID doesn't resolve to a valid device
        path), retry once letting Scapy auto-select the default interface
        instead of leaving the sniffer thread dead."""
        try:
            sniff(iface=self._interface, prn=handler, store=False, stop_filter=stop_filter)
        except OSError as exc:
            if self._interface is None:
                raise
            logger.warning(
                "Could not open interface %s (%s) — retrying with the default interface.",
                self._interface, exc,
            )
            self._interface = None
            sniff(iface=None, prn=handler, store=False, stop_filter=stop_filter)
