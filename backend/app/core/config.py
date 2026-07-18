"""
Centralized application configuration.

All tunable values live here so the rest of the codebase never hardcodes
magic numbers. Values can be overridden via environment variables or a
.env file at the project root (see pydantic-settings docs).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "NetScope"
    api_prefix: str = "/api"

    # Networking
    default_interface: str | None = None  # None => scapy picks the default
    max_packets_in_memory: int = 5000

    # Detection thresholds
    port_scan_threshold: int = 15          # distinct ports from one IP within window
    port_scan_window_seconds: int = 10
    ping_flood_threshold: int = 50         # ICMP echo requests from one IP within window
    ping_flood_window_seconds: int = 5
    high_volume_threshold: int = 300       # packets from one IP within window
    high_volume_window_seconds: int = 10
    suspicious_ports: set[int] = {23, 135, 139, 445, 3389, 4444, 5555, 31337}

    # Database
    database_url: str = "sqlite:///./netscope.db"

    # Websocket broadcast
    broadcast_interval_seconds: float = 1.0

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
