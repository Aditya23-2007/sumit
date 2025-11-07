from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.maintenance_task import TaskPriority


class MaintenanceTaskBase(BaseModel):
    task_name: str
    task_description: Optional[str] = None
    priority: TaskPriority
    estimated_duration_hours: Optional[int] = None
    required_tools: Optional[List[str]] = None


class MaintenanceTaskCreate(MaintenanceTaskBase):
    equipment_id: str


class MaintenanceTaskUpdate(BaseModel):
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    estimated_duration_hours: Optional[int] = None
    required_tools: Optional[List[str]] = None


class MaintenanceTask(MaintenanceTaskBase):
    id: str
    equipment_id: str
    created_at: datetime

    class Config:
        from_attributes = True