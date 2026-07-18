from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    alert_type: str
    severity: str = "medium"
    source_ip: str
    description: str


class AlertCreate(AlertBase):
    pass


class AlertOut(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    acknowledged: int = 0


class AlertAck(BaseModel):
    acknowledged: bool
