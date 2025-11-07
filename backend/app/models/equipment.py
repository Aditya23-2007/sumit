from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime
import enum


class EquipmentStatus(enum.Enum):
    active = "active"
    maintenance = "maintenance"
    retired = "retired"


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    ai_generated_description = Column(Text)
    maintenance_interval_months = Column(Integer)
    last_maintenance_date = Column(DateTime)
    next_maintenance_date = Column(DateTime)
    status = Column(Enum(EquipmentStatus), default=EquipmentStatus.active)
    qr_code_id = Column(String(255), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="equipment")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="equipment")
    maintenance_logs = relationship("MaintenanceLog", back_populates="equipment")
    alerts = relationship("MaintenanceAlert", back_populates="equipment")