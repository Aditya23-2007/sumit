from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User as UserModel, UserRole
from app.models.equipment import Equipment as EquipmentModel
from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
from app.models.maintenance_task import MaintenanceTask as MaintenanceTaskModel
from app.api.v1.endpoints.auth import get_current_active_user
from app.schemas.user import UserInDB
from app.schemas.maintenance_log import MaintenanceLog, MaintenanceLogCreate
from app.schemas.maintenance_task import MaintenanceTask
from app.services.maintenance_service import MaintenanceService

router = APIRouter()


def check_maintenance_permission(
    current_user: UserInDB, action: str = "read"
) -> bool:
    if action == "read":
        return True  # All roles can read maintenance info
    elif action == "complete":
        return current_user.role in [UserRole.admin, UserRole.technician]
    return False


@router.get("/schedule", response_model=List[dict])
async def get_maintenance_schedule(
    days_ahead: int = Query(30, description="Days ahead to schedule"),
    department_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    maintenance_service = MaintenanceService(db)

    # Get upcoming maintenance
    end_date = datetime.utcnow() + timedelta(days=days_ahead)

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        department_id = current_user.department_id

    schedule = await maintenance_service.get_upcoming_maintenance(
        end_date=end_date,
        department_id=department_id
    )

    return schedule


@router.post("/complete", response_model=MaintenanceLog)
async def complete_maintenance(
    maintenance_log: MaintenanceLogCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_maintenance_permission(current_user, "complete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Verify equipment exists and user has access
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == maintenance_log.equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Create maintenance log
    db_maintenance_log = MaintenanceLogModel(
        equipment_id=maintenance_log.equipment_id,
        performed_by=current_user.id,
        tasks_completed=maintenance_log.tasks_completed,
        notes=maintenance_log.notes,
        duration_hours=maintenance_log.duration_hours,
        cost=maintenance_log.cost
    )

    db.add(db_maintenance_log)

    # Update equipment last maintenance date and calculate next maintenance date
    equipment.last_maintenance_date = datetime.utcnow()
    if equipment.maintenance_interval_months:
        equipment.next_maintenance_date = (
            datetime.utcnow() + timedelta(days=equipment.maintenance_interval_months * 30)
        )

    db.commit()
    db.refresh(db_maintenance_log)

    # Trigger AI analysis for next maintenance scheduling
    maintenance_service = MaintenanceService(db)
    await maintenance_service.schedule_next_maintenance(equipment.id)

    return db_maintenance_log


@router.get("/history/{equipment_id}", response_model=List[MaintenanceLog])
async def get_maintenance_history(
    equipment_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify equipment exists and user has access
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    logs = (
        db.query(MaintenanceLogModel)
        .filter(MaintenanceLogModel.equipment_id == equipment_id)
        .order_by(MaintenanceLogModel.performed_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return logs


@router.get("/tasks/{equipment_id}", response_model=List[MaintenanceTask])
async def get_maintenance_tasks(
    equipment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Verify equipment exists and user has access
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    tasks = (
        db.query(MaintenanceTaskModel)
        .filter(MaintenanceTaskModel.equipment_id == equipment_id)
        .order_by(MaintenanceTaskModel.priority.desc())
        .all()
    )

    return tasks


@router.get("/my-tasks", response_model=List[dict])
async def get_my_maintenance_tasks(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_maintenance_permission(current_user, "read"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    maintenance_service = MaintenanceService(db)

    # Get tasks assigned to current user based on their department
    tasks = await maintenance_service.get_user_maintenance_tasks(
        user_id=current_user.id,
        department_id=current_user.department_id
    )

    return tasks


@router.get("/overdue", response_model=List[dict])
async def get_overdue_maintenance(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    maintenance_service = MaintenanceService(db)

    # Filter by department if not admin
    department_id = None
    if current_user.role != UserRole.admin and current_user.department_id:
        department_id = current_user.department_id

    overdue_items = await maintenance_service.get_overdue_maintenance(
        department_id=department_id
    )

    return overdue_items