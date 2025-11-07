from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User as UserModel, UserRole
from app.models.equipment import Equipment as EquipmentModel
from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
from app.api.v1.endpoints.auth import get_current_active_user
from app.schemas.user import UserInDB
from app.schemas.maintenance_alert import MaintenanceAlert, AlertCreate, AlertAcknowledge
from app.services.alert_service import AlertService

router = APIRouter()


def check_alert_permission(
    current_user: UserInDB, action: str = "read"
) -> bool:
    if action == "read":
        return True  # All roles can read alerts
    elif action == "acknowledge":
        return current_user.role in [UserRole.admin, UserRole.technician]
    return False


@router.get("/", response_model=List[MaintenanceAlert])
async def get_alerts(
    skip: int = 0,
    limit: int = 100,
    alert_type: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceAlertModel)

    # Filter by department equipment if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        # Get equipment IDs from user's department
        equipment_ids = (
            db.query(EquipmentModel.id)
            .filter(EquipmentModel.department_id == current_user.department_id)
            .subquery()
        )
        query = query.filter(MaintenanceAlertModel.equipment_id.in_(equipment_ids))

    if alert_type:
        query = query.filter(MaintenanceAlertModel.alert_type == alert_type)

    if acknowledged is not None:
        if acknowledged:
            query = query.filter(MaintenanceAlertModel.acknowledged_at.isnot(None))
        else:
            query = query.filter(MaintenanceAlertModel.acknowledged_at.is_(None))

    alerts = query.order_by(MaintenanceAlertModel.created_at.desc()).offset(skip).limit(limit).all()
    return alerts


@router.get("/active", response_model=List[MaintenanceAlert])
async def get_active_alerts(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceAlertModel).filter(
        MaintenanceAlertModel.acknowledged_at.is_(None)
    )

    # Filter by department equipment if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        equipment_ids = (
            db.query(EquipmentModel.id)
            .filter(EquipmentModel.department_id == current_user.department_id)
            .subquery()
        )
        query = query.filter(MaintenanceAlertModel.equipment_id.in_(equipment_ids))

    alerts = query.order_by(MaintenanceAlertModel.created_at.desc()).all()
    return alerts


@router.put("/{alert_id}/acknowledge", response_model=MaintenanceAlert)
async def acknowledge_alert(
    alert_id: str,
    acknowledge_data: AlertAcknowledge,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not check_alert_permission(current_user, "acknowledge"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    alert = db.query(MaintenanceAlertModel).filter(MaintenanceAlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check department access
    equipment = db.query(EquipmentModel).filter(EquipmentModel.id == alert.equipment_id).first()
    if (current_user.role != UserRole.admin and
        equipment.department_id != current_user.department_id):
        raise HTTPException(status_code=403, detail="Access denied")

    if acknowledge_data.acknowledged and not alert.acknowledged_at:
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = current_user.id

    db.commit()
    db.refresh(alert)

    return alert


@router.post("/test", response_model=dict)
async def test_alert_system(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    alert_service = AlertService(db)
    test_result = await alert_service.send_test_alert(current_user.email)

    return test_result


@router.get("/count", response_model=dict)
async def get_alert_counts(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceAlertModel)

    # Filter by department equipment if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        equipment_ids = (
            db.query(EquipmentModel.id)
            .filter(EquipmentModel.department_id == current_user.department_id)
            .subquery()
        )
        query = query.filter(MaintenanceAlertModel.equipment_id.in_(equipment_ids))

    total_alerts = query.count()
    unacknowledged = query.filter(MaintenanceAlertModel.acknowledged_at.is_(None)).count()

    # Count by type
    due_soon = query.filter(
        MaintenanceAlertModel.acknowledged_at.is_(None),
        MaintenanceAlertModel.alert_type == "due_soon"
    ).count()

    overdue = query.filter(
        MaintenanceAlertModel.acknowledged_at.is_(None),
        MaintenanceAlertModel.alert_type == "overdue"
    ).count()

    predicted_failure = query.filter(
        MaintenanceAlertModel.acknowledged_at.is_(None),
        MaintenanceAlertModel.alert_type == "predicted_failure"
    ).count()

    return {
        "total_alerts": total_alerts,
        "unacknowledged": unacknowledged,
        "due_soon": due_soon,
        "overdue": overdue,
        "predicted_failure": predicted_failure
    }


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    alert = db.query(MaintenanceAlertModel).filter(MaintenanceAlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"message": "Alert deleted successfully"}