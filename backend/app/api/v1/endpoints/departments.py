from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User as UserModel, UserRole
from app.models.department import Department as DepartmentModel
from app.api.v1.endpoints.auth import get_current_active_user
from app.schemas.user import UserInDB
from app.schemas.department import Department, DepartmentCreate, DepartmentUpdate

router = APIRouter()


def check_department_permission(
    current_user: UserInDB, action: str = "read"
) -> bool:
    if action == "read":
        return True  # All roles can read departments
    elif action in ["create", "update"]:
        return current_user.role == UserRole.admin
    return False


@router.get("/", response_model=List[Department])
async def get_departments(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # If not admin, only return user's department
    if current_user.role != UserRole.admin:
        if current_user.department_id:
            department = db.query(DepartmentModel).filter(DepartmentModel.id == current_user.department_id).first()
            return [department] if department else []
        else:
            return []

    departments = db.query(DepartmentModel).all()
    return departments


@router.get("/{department_id}", response_model=Department)
async def get_department_by_id(
    department_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Check access if not admin
    if (current_user.role != UserRole.admin and
        department.id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return department


@router.post("/", response_model=Department)
async def create_department(
    department: DepartmentCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_department_permission(current_user, "create"):
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if department name already exists
    existing = db.query(DepartmentModel).filter(DepartmentModel.name == department.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department with this name already exists")

    db_department = DepartmentModel(
        name=department.name,
        description=department.description,
        location=department.location
    )

    db.add(db_department)
    db.commit()
    db.refresh(db_department)

    return db_department


@router.put("/{department_id}", response_model=Department)
async def update_department(
    department_id: str,
    department_update: DepartmentUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_department_permission(current_user, "update"):
        raise HTTPException(status_code=403, detail="Admin access required")

    department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    # Update fields
    update_data = department_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)

    return department


@router.get("/{department_id}/equipment-count")
async def get_department_equipment_count(
    department_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check access
    if (current_user.role != UserRole.admin and
        department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    from app.models.equipment import Equipment as EquipmentModel

    count = (
        db.query(EquipmentModel)
        .filter(EquipmentModel.department_id == department_id)
        .count()
    )

    return {"department_id": department_id, "equipment_count": count}


@router.get("/{department_id}/stats")
async def get_department_stats(
    department_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check access
    if (current_user.role != UserRole.admin and
        department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    from app.models.equipment import Equipment as EquipmentModel
    from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
    from app.models.user import User as UserModel
    from datetime import datetime, timedelta

    # Equipment stats
    total_equipment = (
        db.query(EquipmentModel)
        .filter(EquipmentModel.department_id == department_id)
        .count()
    )

    active_equipment = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            EquipmentModel.status == "active"
        )
        .count()
    )

    # Maintenance due (next 30 days)
    thirty_days_from_now = datetime.utcnow() + timedelta(days=30)
    due_soon = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            EquipmentModel.next_maintenance_date <= thirty_days_from_now,
            EquipmentModel.next_maintenance_date >= datetime.utcnow()
        )
        .count()
    )

    # Overdue
    overdue = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            EquipmentModel.next_maintenance_date < datetime.utcnow()
        )
        .count()
    )

    # Active alerts
    active_alerts = (
        db.query(MaintenanceAlertModel)
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceAlertModel.acknowledged_at.is_(None)
        )
        .count()
    )

    # Users in department
    users_count = (
        db.query(UserModel)
        .filter(UserModel.department_id == department_id)
        .count()
    )

    return {
        "department_id": department_id,
        "total_equipment": total_equipment,
        "active_equipment": active_equipment,
        "due_soon": due_soon,
        "overdue": overdue,
        "active_alerts": active_alerts,
        "users_count": users_count
    }