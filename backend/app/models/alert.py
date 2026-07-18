from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database.session import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    alert_type = Column(String(64), index=True)   # PORT_SCAN / PING_FLOOD / HIGH_VOLUME / SUSPICIOUS_PORT
    severity = Column(String(16), default="medium")  # low / medium / high
    source_ip = Column(String(45), index=True)
    description = Column(Text)
    acknowledged = Column(Integer, default=0)  # 0/1 boolean, sqlite-friendly
