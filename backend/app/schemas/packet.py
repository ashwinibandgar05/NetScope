from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PacketBase(BaseModel):
    src_ip: str
    dst_ip: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: str
    app_protocol: Optional[str] = None
    length: int
    ttl: Optional[int] = None
    flags: Optional[str] = None
    raw_summary: Optional[str] = None


class PacketCreate(PacketBase):
    session_id: Optional[int] = None


class PacketOut(PacketBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: Optional[int] = None
    timestamp: datetime


class PacketDetail(PacketOut):
    """Extended payload shown in the side panel — same fields today, kept
    as a distinct schema so we can extend it (e.g. hex payload) without
    touching the list endpoint's contract."""
    pass
