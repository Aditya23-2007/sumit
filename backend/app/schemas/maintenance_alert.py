from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.maintenance_alert import AlertType


class AlertCreate(BaseModel):
    equipment_id: str
    alert_type: AlertType
    message: str
    scheduled_date: Optional[datetime] = None


class AlertAcknowledge(BaseModel):
    acknowledged: bool = True


class MaintenanceAlert(BaseModel):
    id: str
    equipment_id: str
    alert_type: AlertType
    message: str
    scheduled_date: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    class Config:
        from_attributes = True