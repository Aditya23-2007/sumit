from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime
import enum


class AlertType(enum.Enum):
    due_soon = "due_soon"
    overdue = "overdue"
    predicted_failure = "predicted_failure"


class MaintenanceAlert(Base):
    __tablename__ = "maintenance_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    alert_type = Column(Enum(AlertType), nullable=False)
    message = Column(Text, nullable=False)
    scheduled_date = Column(DateTime)
    sent_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    equipment = relationship("Equipment", back_populates="alerts")
    acknowledged_by_user = relationship("User", foreign_keys=[acknowledged_by], back_populates="acknowledged_alerts")