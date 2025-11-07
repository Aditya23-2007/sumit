from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.user import User as UserModel, UserRole
from app.models.equipment import Equipment as EquipmentModel
from app.models.department import Department as DepartmentModel
from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
from app.api.v1.endpoints.auth import get_current_active_user
from app.schemas.user import UserInDB

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Base query for equipment - filtered by department if not admin
    equipment_query = db.query(EquipmentModel)
    if current_user.role != UserRole.admin and current_user.department_id:
        equipment_query = equipment_query.filter(EquipmentModel.department_id == current_user.department_id)

    # Equipment stats
    total_equipment = equipment_query.count()
    active_equipment = equipment_query.filter(EquipmentModel.status == "active").count()
    maintenance_equipment = equipment_query.filter(EquipmentModel.status == "maintenance").count()

    # Maintenance stats
    now = datetime.utcnow()
    thirty_days_from_now = now + timedelta(days=30)

    # Use the same filtered query for maintenance calculations
    due_soon = equipment_query.filter(
        EquipmentModel.next_maintenance_date <= thirty_days_from_now,
        EquipmentModel.next_maintenance_date >= now
    ).count()

    overdue = equipment_query.filter(
        EquipmentModel.next_maintenance_date < now
    ).count()

    # Alert stats
    alert_query = db.query(MaintenanceAlertModel).join(EquipmentModel)
    if current_user.role != UserRole.admin and current_user.department_id:
        alert_query = alert_query.filter(EquipmentModel.department_id == current_user.department_id)

    total_alerts = alert_query.count()
    active_alerts = alert_query.filter(MaintenanceAlertModel.acknowledged_at.is_(None)).count()

    return {
        "equipment": {
            "total": total_equipment,
            "active": active_equipment,
            "maintenance": maintenance_equipment,
            "due_soon": due_soon,
            "overdue": overdue
        },
        "alerts": {
            "total": total_alerts,
            "active": active_alerts
        }
    }


@router.get("/upcoming-maintenance")
async def get_upcoming_maintenance(
    days: int = Query(30, description="Days ahead to look"),
    limit: int = Query(10, description="Maximum number of items"),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    end_date = datetime.utcnow() + timedelta(days=days)

    query = (
        db.query(
            EquipmentModel,
            DepartmentModel.name.label("department_name")
        )
        .join(DepartmentModel)
        .filter(
            EquipmentModel.next_maintenance_date >= datetime.utcnow(),
            EquipmentModel.next_maintenance_date <= end_date,
            EquipmentModel.status == "active"
        )
        .order_by(EquipmentModel.next_maintenance_date.asc())
        .limit(limit)
    )

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        query = query.filter(EquipmentModel.department_id == current_user.department_id)

    results = query.all()

    upcoming_maintenance = []
    for equipment, department_name in results:
        days_until_maintenance = (equipment.next_maintenance_date - datetime.utcnow()).days

        upcoming_maintenance.append({
            "equipment_id": str(equipment.id),
            "equipment_name": equipment.name,
            "department_name": department_name,
            "next_maintenance_date": equipment.next_maintenance_date,
            "days_until_maintenance": days_until_maintenance,
            "priority": "high" if days_until_maintenance <= 7 else "medium"
        })

    return upcoming_maintenance


@router.get("/recent-alerts")
async def get_recent_alerts(
    limit: int = Query(10, description="Maximum number of alerts"),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            MaintenanceAlertModel,
            EquipmentModel.name.label("equipment_name"),
            DepartmentModel.name.label("department_name")
        )
        .join(EquipmentModel)
        .join(DepartmentModel)
        .filter(MaintenanceAlertModel.acknowledged_at.is_(None))
        .order_by(MaintenanceAlertModel.created_at.desc())
        .limit(limit)
    )

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        query = query.filter(EquipmentModel.department_id == current_user.department_id)

    results = query.all()

    alerts = []
    for alert, equipment_name, department_name in results:
        alerts.append({
            "alert_id": str(alert.id),
            "equipment_id": str(alert.equipment_id),
            "equipment_name": equipment_name,
            "department_name": department_name,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "created_at": alert.created_at
        })

    return alerts


@router.get("/maintenance-performance")
async def get_maintenance_performance(
    days: int = Query(30, description="Days to look back"),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)

    # Base query for maintenance logs
    logs_query = (
        db.query(MaintenanceLogModel)
        .join(EquipmentModel)
        .filter(MaintenanceLogModel.performed_at >= start_date)
    )

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        logs_query = logs_query.filter(EquipmentModel.department_id == current_user.department_id)

    # Maintenance completed
    completed_maintenance = logs_query.count()

    # Average duration
    avg_duration_result = (
        logs_query.filter(MaintenanceLogModel.duration_hours.isnot(None))
        .with_entities(func.avg(MaintenanceLogModel.duration_hours))
        .scalar()
    )
    avg_duration = float(avg_duration_result) if avg_duration_result else 0

    # Total cost
    total_cost_result = (
        logs_query.filter(MaintenanceLogModel.cost.isnot(None))
        .with_entities(func.sum(MaintenanceLogModel.cost))
        .scalar()
    )
    total_cost = float(total_cost_result) if total_cost_result else 0

    # Top performers (equipment with most maintenance)
    top_equipment = (
        logs_query.join(EquipmentModel)
        .with_entities(
            EquipmentModel.name,
            func.count(MaintenanceLogModel.id).label("maintenance_count")
        )
        .group_by(EquipmentModel.id, EquipmentModel.name)
        .order_by(func.count(MaintenanceLogModel.id).desc())
        .limit(5)
        .all()
    )

    return {
        "period_days": days,
        "completed_maintenance": completed_maintenance,
        "average_duration_hours": round(avg_duration, 1),
        "total_cost": round(total_cost, 2),
        "top_equipment": [
            {
                "equipment_name": name,
                "maintenance_count": count
            }
            for name, count in top_equipment
        ]
    }


@router.get("/equipment-by-department")
async def get_equipment_by_department(
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = (
        db.query(
            DepartmentModel.name,
            func.count(EquipmentModel.id).label("equipment_count"),
            func.sum(
                func.case(
                    (EquipmentModel.status == "active", 1),
                    else_=0
                )
            ).label("active_count")
        )
        .join(EquipmentModel, DepartmentModel.id == EquipmentModel.department_id)
        .group_by(DepartmentModel.id, DepartmentModel.name)
    )

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        query = query.filter(DepartmentModel.id == current_user.department_id)

    results = query.all()

    equipment_by_department = [
        {
            "department_name": name,
            "total_equipment": count,
            "active_equipment": active_count
        }
        for name, count, active_count in results
    ]

    return equipment_by_department


@router.get("/alerts-timeline")
async def get_alerts_timeline(
    days: int = Query(7, description="Days to look back"),
    current_user: UserInDB = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        db.query(
            func.date(MaintenanceAlertModel.created_at).label("date"),
            MaintenanceAlertModel.alert_type,
            func.count(MaintenanceAlertModel.id).label("count")
        )
        .join(EquipmentModel)
        .filter(MaintenanceAlertModel.created_at >= start_date)
        .group_by(
            func.date(MaintenanceAlertModel.created_at),
            MaintenanceAlertModel.alert_type
        )
        .order_by(func.date(MaintenanceAlertModel.created_at).asc())
    )

    # Filter by department if not admin
    if current_user.role != UserRole.admin and current_user.department_id:
        query = query.filter(EquipmentModel.department_id == current_user.department_id)

    results = query.all()

    timeline = {}
    for date, alert_type, count in results:
        date_str = date.isoformat()
        if date_str not in timeline:
            timeline[date_str] = {"due_soon": 0, "overdue": 0, "predicted_failure": 0}
        timeline[date_str][alert_type] = count

    return timeline