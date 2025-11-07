from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal


class MaintenanceLogCreate(BaseModel):
    equipment_id: str
    tasks_completed: Dict[str, bool]
    notes: Optional[str] = None
    duration_hours: Optional[int] = None
    cost: Optional[Decimal] = None


class MaintenanceLog(BaseModel):
    id: str
    equipment_id: str
    performed_by: str
    tasks_completed: Dict[str, bool]
    notes: Optional[str] = None
    duration_hours: Optional[int] = None
    cost: Optional[Decimal] = None
    performed_at: datetime

    class Config:
        from_attributes = True