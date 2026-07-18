from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database.session import Base


class CaptureSession(Base):
    __tablename__ = "capture_sessions"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    interface = Column(String(64), nullable=True)
    total_packets = Column(Integer, default=0)
    status = Column(String(16), default="running")  # running / stopped

    packets = relationship("Packet", back_populates="capture_session")
