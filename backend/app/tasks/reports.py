from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.email_service import EmailService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.reports.generate_weekly_report")
def generate_weekly_report(self):
    """Generate weekly maintenance reports for departments"""
    try:
        db = SessionLocal()
        email_service = EmailService()

        # Get all departments
        from app.models.department import Department as DepartmentModel
        departments = db.query(DepartmentModel).all()

        # Define the week period (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        reports_generated = 0
        errors = []

        for department in departments:
            try:
                report_data = await _generate_department_weekly_report(
                    db, department.id, start_date, end_date
                )

                # Get department admins to send report
                from app.models.user import User as UserModel
                admins = (
                    db.query(UserModel)
                    .filter(
                        UserModel.department_id == department.id,
                        UserModel.role == "admin"
                    )
                    .all()
                )

                if admins:
                    # Send report to each admin
                    for admin in admins:
                        await email_service.send_weekly_report(
                            recipient_email=admin.email,
                            report_data=report_data
                        )

                    reports_generated += 1
                    logger.info(f"Weekly report generated and sent for {department.name}")

            except Exception as dept_error:
                error_msg = f"Failed to generate weekly report for {department.name}: {str(dept_error)}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Weekly reports completed. Generated: {reports_generated}, Errors: {len(errors)}")
        return {
            "status": "success",
            "reports_generated": reports_generated,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Weekly report generation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.reports.generate_monthly_report")
def generate_monthly_report(self):
    """Generate monthly maintenance reports"""
    try:
        db = SessionLocal()
        email_service = EmailService()

        # Get all departments
        from app.models.department import Department as DepartmentModel
        departments = db.query(DepartmentModel).all()

        # Define the month period (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        reports_generated = 0
        errors = []

        for department in departments:
            try:
                report_data = await _generate_department_monthly_report(
                    db, department.id, start_date, end_date
                )

                # Get department admins to send report
                from app.models.user import User as UserModel
                admins = (
                    db.query(UserModel)
                    .filter(
                        UserModel.department_id == department.id,
                        UserModel.role == "admin"
                    )
                    .all()
                )

                if admins:
                    # Send report to each admin
                    for admin in admins:
                        await email_service.send_monthly_report(
                            recipient_email=admin.email,
                            report_data=report_data
                        )

                    reports_generated += 1
                    logger.info(f"Monthly report generated and sent for {department.name}")

            except Exception as dept_error:
                error_msg = f"Failed to generate monthly report for {department.name}: {str(dept_error)}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(f"Monthly reports completed. Generated: {reports_generated}, Errors: {len(errors)}")
        return {
            "status": "success",
            "reports_generated": reports_generated,
            "errors": errors
        }

    except Exception as e:
        logger.error(f"Monthly report generation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


async def _generate_department_weekly_report(db, department_id: str, start_date: datetime, end_date: datetime):
    """Generate weekly report data for a specific department"""
    from app.models.equipment import Equipment as EquipmentModel
    from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
    from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
    from sqlalchemy import func, and_

    # Get department info
    from app.models.department import Department as DepartmentModel
    department = db.query(DepartmentModel).filter(DepartmentModel.id == department_id).first()

    # Equipment statistics
    total_equipment = db.query(EquipmentModel).filter(EquipmentModel.department_id == department_id).count()
    active_equipment = db.query(EquipmentModel).filter(
        EquipmentModel.department_id == department_id,
        EquipmentModel.status == "active"
    ).count()

    # Maintenance completed this week
    completed_maintenance = (
        db.query(MaintenanceLogModel)
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date
        )
        .count()
    )

    # Total maintenance time this week
    total_time = (
        db.query(func.sum(MaintenanceLogModel.duration_hours))
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date,
            MaintenanceLogModel.duration_hours.isnot(None)
        )
        .scalar() or 0
    )

    # Alerts generated this week
    alerts_generated = (
        db.query(MaintenanceAlertModel)
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceAlertModel.created_at >= start_date,
            MaintenanceAlertModel.created_at <= end_date
        )
        .count()
    )

    # Critical alerts this week
    critical_alerts = (
        db.query(MaintenanceAlertModel)
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceAlertModel.created_at >= start_date,
            MaintenanceAlertModel.created_at <= end_date,
            MaintenanceAlertModel.alert_type.in_(["overdue", "predicted_failure"])
        )
        .count()
    )

    # Overdue equipment
    overdue_equipment = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            EquipmentModel.next_maintenance_date < datetime.utcnow(),
            EquipmentModel.status == "active"
        )
        .count()
    )

    # Upcoming maintenance (next 7 days)
    next_week = datetime.utcnow() + timedelta(days=7)
    upcoming_maintenance = (
        db.query(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            EquipmentModel.next_maintenance_date >= datetime.utcnow(),
            EquipmentModel.next_maintenance_date <= next_week,
            EquipmentModel.status == "active"
        )
        .count()
    )

    return {
        "report_type": "weekly",
        "department_name": department.name if department else "Unknown",
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date.strftime("%Y-%m-%d"),
        "equipment_stats": {
            "total_equipment": total_equipment,
            "active_equipment": active_equipment,
            "overdue_equipment": overdue_equipment,
            "upcoming_maintenance": upcoming_maintenance
        },
        "maintenance_stats": {
            "completed_maintenance": completed_maintenance,
            "total_hours": total_time,
            "average_duration": total_time / completed_maintenance if completed_maintenance > 0 else 0
        },
        "alert_stats": {
            "alerts_generated": alerts_generated,
            "critical_alerts": critical_alerts
        }
    }


async def _generate_department_monthly_report(db, department_id: str, start_date: datetime, end_date: datetime):
    """Generate monthly report data for a specific department"""
    # Similar to weekly report but with monthly aggregations and trends
    weekly_data = await _generate_department_weekly_report(db, department_id, start_date, end_date)
    weekly_data["report_type"] = "monthly"

    # Add monthly-specific metrics
    from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
    from app.models.equipment import Equipment as EquipmentModel
    from sqlalchemy import func

    # Cost analysis
    total_cost = (
        db.query(func.sum(MaintenanceLogModel.cost))
        .join(EquipmentModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date,
            MaintenanceLogModel.cost.isnot(None)
        )
        .scalar() or 0
    )

    # Top equipment by maintenance frequency
    top_equipment = (
        db.query(
            EquipmentModel.name,
            func.count(MaintenanceLogModel.id).label("maintenance_count")
        )
        .join(MaintenanceLogModel)
        .filter(
            EquipmentModel.department_id == department_id,
            MaintenanceLogModel.performed_at >= start_date,
            MaintenanceLogModel.performed_at <= end_date
        )
        .group_by(EquipmentModel.id, EquipmentModel.name)
        .order_by(func.count(MaintenanceLogModel.id).desc())
        .limit(5)
        .all()
    )

    weekly_data["cost_analysis"] = {
        "total_cost": float(total_cost),
        "average_cost_per_maintenance": float(total_cost) / weekly_data["maintenance_stats"]["completed_maintenance"] if weekly_data["maintenance_stats"]["completed_maintenance"] > 0 else 0
    }

    weekly_data["top_equipment"] = [
        {"name": name, "maintenance_count": count} for name, count in top_equipment
    ]

    return weekly_data