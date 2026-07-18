from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class Packet(Base):
    __tablename__ = "packets"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("capture_sessions.id"), nullable=True, index=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    src_ip = Column(String(45), index=True)
    dst_ip = Column(String(45), index=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    protocol = Column(String(16), index=True)   # TCP / UDP / ICMP / ARP / OTHER
    app_protocol = Column(String(16), nullable=True)  # HTTP / HTTPS / DNS guess
    length = Column(Integer, default=0)
    ttl = Column(Integer, nullable=True)
    flags = Column(String(32), nullable=True)
    raw_summary = Column(Text, nullable=True)   # scapy .summary() for detail panel

    capture_session = relationship("CaptureSession", back_populates="packets")
