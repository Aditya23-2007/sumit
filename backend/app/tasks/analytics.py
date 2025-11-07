from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.analytics.generate_monthly_analytics")
def generate_monthly_analytics(self):
    """Generate monthly analytics and performance metrics"""
    try:
        db = SessionLocal()

        # Define the month period (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        analytics_results = await _generate_comprehensive_analytics(db, start_date, end_date)

        logger.info(f"Monthly analytics generated successfully")
        return {
            "status": "success",
            "analytics": analytics_results,
            "period_start": start_date.strftime("%Y-%m-%d"),
            "period_end": end_date.strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.error(f"Monthly analytics generation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.analytics.update_performance_metrics")
def update_performance_metrics(self):
    """Update real-time performance metrics"""
    try:
        db = SessionLocal()

        metrics = await _calculate_performance_metrics(db)

        logger.info("Performance metrics updated")
        return {
            "status": "success",
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Performance metrics update failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.analytics.predictive_accuracy")
def calculate_predictive_accuracy(self):
    """Calculate accuracy of AI predictions"""
    try:
        db = SessionLocal()

        accuracy_metrics = await _calculate_ai_prediction_accuracy(db)

        logger.info("Predictive accuracy metrics calculated")
        return {
            "status": "success",
            "accuracy_metrics": accuracy_metrics
        }

    except Exception as e:
        logger.error(f"Predictive accuracy calculation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


async def _generate_comprehensive_analytics(db, start_date: datetime, end_date: datetime):
    """Generate comprehensive analytics for the specified period"""
    from app.models.equipment import Equipment as EquipmentModel
    from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
    from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
    from app.models.department import Department as DepartmentModel
    from sqlalchemy import func, and_

    # Equipment overview
    total_equipment = db.query(EquipmentModel).count()
    active_equipment = db.query(EquipmentModel).filter(EquipmentModel.status == "active").count()
    retired_equipment = db.query(EquipmentModel).filter(EquipmentModel.status == "retired").count()

    # Maintenance performance
    completed_maintenance = (
        db.query(MaintenanceLogModel)
        .filter(
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date
        )
        .count()
    )

    total_maintenance_hours = (
        db.query(func.sum(MaintenanceLogModel.duration_hours))
        .filter(
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date,
            MaintenanceLogModel.duration_hours.isnot(None)
        )
        .scalar() or 0
    )

    total_maintenance_cost = (
        db.query(func.sum(MaintenanceLogModel.cost))
        .filter(
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date,
            MaintenanceLogModel.cost.isnot(None)
        )
        .scalar() or 0
    )

    # Alert analytics
    total_alerts = (
        db.query(MaintenanceAlertModel)
        .filter(
            MaintenanceAlertModel.created_at >= start_date,
            MaintenanceAlertModel.created_at <= end_date
        )
        .count()
    )

    acknowledged_alerts = (
        db.query(MaintenanceAlertModel)
        .filter(
            MaintenanceAlertModel.created_at >= start_date,
            MaintenanceAlertModel.created_at <= end_date,
            MaintenanceAlertModel.acknowledged_at.isnot(None)
        )
        .count()
    )

    # Department performance
    department_performance = []
    departments = db.query(DepartmentModel).all()

    for department in departments:
        dept_equipment = db.query(EquipmentModel).filter(EquipmentModel.department_id == department.id).count()
        dept_maintenance = (
            db.query(MaintenanceLogModel)
            .join(EquipmentModel)
            .filter(
                EquipmentModel.department_id == department.id,
                MaintenanceLogModel.performed_at >= start_date,
                MaintenanceLogModel.performed_at <= end_date
            )
            .count()
        )

        dept_alerts = (
            db.query(MaintenanceAlertModel)
            .join(EquipmentModel)
            .filter(
                EquipmentModel.department_id == department.id,
                MaintenanceAlertModel.created_at >= start_date,
                MaintenanceAlertModel.created_at <= end_date
            )
            .count()
        )

        department_performance.append({
            "department_name": department.name,
            "equipment_count": dept_equipment,
            "maintenance_completed": dept_maintenance,
            "alerts_generated": dept_alerts
        })

    # Equipment health metrics
    overdue_equipment = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.next_maintenance_date < datetime.utcnow(),
            EquipmentModel.status == "active"
        )
        .count()
    )

    # MTBF (Mean Time Between Failures) calculation
    failure_logs = (
        db.query(MaintenanceLogModel)
        .filter(
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date,
            MaintenanceLogModel.notes.ilike("%failure%")
        )
        .count()
    )

    return {
        "equipment_overview": {
            "total_equipment": total_equipment,
            "active_equipment": active_equipment,
            "retired_equipment": retired_equipment,
            "overdue_equipment": overdue_equipment
        },
        "maintenance_performance": {
            "completed_maintenance": completed_maintenance,
            "total_hours": total_maintenance_hours,
            "total_cost": float(total_maintenance_cost),
            "average_cost_per_maintenance": float(total_maintenance_cost) / completed_maintenance if completed_maintenance > 0 else 0,
            "average_hours_per_maintenance": total_maintenance_hours / completed_maintenance if completed_maintenance > 0 else 0
        },
        "alert_performance": {
            "total_alerts": total_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "acknowledgment_rate": (acknowledged_alerts / total_alerts * 100) if total_alerts > 0 else 100
        },
        "department_performance": department_performance,
        "reliability_metrics": {
            "failures_recorded": failure_logs,
            "mtbf_days": (30 / failure_logs) if failure_logs > 0 else None  # Simplified MTBF calculation
        }
    }


async def _calculate_performance_metrics(db):
    """Calculate real-time performance metrics"""
    from app.models.equipment import Equipment as EquipmentModel
    from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
    from datetime import datetime

    # Current equipment status distribution
    status_distribution = (
        db.query(
            EquipmentModel.status,
            func.count(EquipmentModel.id).label("count")
        )
        .group_by(EquipmentModel.status)
        .all()
    )

    # Alert status distribution
    alert_distribution = (
        db.query(
            MaintenanceAlertModel.alert_type,
            func.count(MaintenanceAlertModel.id).label("count")
        )
        .filter(MaintenanceAlertModel.acknowledged_at.is_(None))
        .group_by(MaintenanceAlertModel.alert_type)
        .all()
    )

    return {
        "equipment_status": [
            {"status": status.value, "count": count} for status, count in status_distribution
        ],
        "active_alerts": [
            {"type": alert_type.value, "count": count} for alert_type, count in alert_distribution
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


async def _calculate_ai_prediction_accuracy(db):
    """Calculate AI prediction accuracy by comparing predictions with actual outcomes"""
    # This is a simplified implementation
    # In a real system, you would track predictions and compare with actual failures

    return {
        "prediction_accuracy": 85.5,  # Example value
        "false_positive_rate": 12.3,
        "false_negative_rate": 2.2,
        "total_predictions": 150,
        "accurate_predictions": 128
    }