from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.equipment import EquipmentStatus


class EquipmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    department_id: str
    maintenance_interval_months: Optional[int] = None


class EquipmentCreate(EquipmentBase):
    usage_intensity: Optional[str] = None
    equipment_type: Optional[str] = None


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    maintenance_interval_months: Optional[int] = None
    status: Optional[EquipmentStatus] = None
    last_maintenance_date: Optional[datetime] = None


class Equipment(EquipmentBase):
    id: str
    ai_generated_description: Optional[str] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    status: EquipmentStatus
    qr_code_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EquipmentWithTasks(Equipment):
    maintenance_tasks: List[dict] = []