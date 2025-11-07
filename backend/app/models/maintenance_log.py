from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id = Column(UUID(as_uuid=True), ForeignKey("equipment.id"))
    performed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    tasks_completed = Column(JSON)
    notes = Column(Text)
    duration_hours = Column(Integer)
    cost = Column(Numeric(10, 2))
    performed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    equipment = relationship("Equipment", back_populates="maintenance_logs")
    performed_by_user = relationship("User", foreign_keys=[performed_by], back_populates="maintenance_logs")