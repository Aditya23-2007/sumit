from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User as UserModel, UserRole
from app.models.equipment import Equipment as EquipmentModel
from app.models.department import Department as DepartmentModel
from app.api.v1.endpoints.auth import get_current_active_user
from app.schemas.user import UserInDB
from app.schemas.equipment import Equipment, EquipmentCreate, EquipmentUpdate, EquipmentWithTasks
from app.services.ai_service import AIService
from app.services.qr_service import QRCodeService
import uuid

router = APIRouter()


def check_equipment_permission(
    current_user: UserInDB, action: str = "read"
) -> bool:
    if action == "read":
        return True  # All roles can read equipment
    elif action in ["create", "update"]:
        return current_user.role in [UserRole.admin, UserRole.technician]
    elif action == "delete":
        return current_user.role == UserRole.admin
    return False


@router.get("/", response_model=List[Equipment])
async def get_equipment(
    skip: int = 0,
    limit: int = 100,
    department_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(EquipmentModel)

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        query = query.filter(EquipmentModel.department_id == current_user.department_id)
    elif department_id:
        query = query.filter(EquipmentModel.department_id == department_id)

    if status:
        query = query.filter(EquipmentModel.status == status)

    equipment = query.offset(skip).limit(limit).all()
    return equipment


@router.get("/{equipment_id}", response_model=EquipmentWithTasks)
async def get_equipment_by_id(
    equipment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access if not admin
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return equipment


@router.post("/", response_model=Equipment)
async def create_equipment(
    equipment: EquipmentCreate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_equipment_permission(current_user, "create"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Verify department exists and user has access
    department = db.query(DepartmentModel).filter(DepartmentModel.id == equipment.department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    if (current_user.role != UserRole.admin and
        department.id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Cannot create equipment in other departments")

    # Generate unique QR code ID
    qr_code_id = str(uuid.uuid4())[:8].upper()

    db_equipment = EquipmentModel(
        name=equipment.name,
        description=equipment.description,
        department_id=equipment.department_id,
        qr_code_id=qr_code_id
    )

    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)

    return db_equipment


@router.post("/{equipment_id}/ai-analyze", response_model=Equipment)
async def ai_analyze_equipment(
    equipment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_equipment_permission(current_user, "update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get department info for AI context
    department = db.query(DepartmentModel).filter(DepartmentModel.id == equipment.department_id).first()

    # Use AI service to analyze equipment
    ai_service = AIService()
    ai_result = await ai_service.analyze_equipment(
        equipment_name=equipment.name,
        department_name=department.name if department else "Unknown",
        equipment_type=equipment.description
    )

    # Update equipment with AI results
    equipment.ai_generated_description = ai_result["description"]
    equipment.maintenance_interval_months = ai_result["maintenance_interval_months"]

    # Create maintenance tasks based on AI recommendations
    from app.models.maintenance_task import MaintenanceTask
    for task_data in ai_result["maintenance_tasks"]:
        task = MaintenanceTask(
            equipment_id=equipment.id,
            task_name=task_data["name"],
            task_description=task_data["description"],
            priority=task_data["priority"],
            estimated_duration_hours=task_data.get("estimated_duration_hours"),
            required_tools=task_data.get("required_tools", [])
        )
        db.add(task)

    db.commit()
    db.refresh(equipment)

    return equipment


@router.put("/{equipment_id}", response_model=Equipment)
async def update_equipment(
    equipment_id: str,
    equipment_update: EquipmentUpdate,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_equipment_permission(current_user, "update"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Update fields
    update_data = equipment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    return equipment


@router.delete("/{equipment_id}")
async def delete_equipment(
    equipment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_equipment_permission(current_user, "delete"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(equipment)
    db.commit()

    return {"message": "Equipment deleted successfully"}


@router.get("/{equipment_id}/qr-code")
async def get_equipment_qr_code(
    equipment_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Check department access
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    qr_service = QRCodeService()
    qr_code_url = await qr_service.generate_equipment_qr_code(
        equipment_id=equipment.id,
        equipment_name=equipment.name
    )

    return {"qr_code_url": qr_code_url}