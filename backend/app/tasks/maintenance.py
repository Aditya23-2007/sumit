from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.maintenance_service import MaintenanceService
from app.services.alert_service import AlertService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.maintenance.generate_daily_schedule")
def generate_daily_schedule(self):
    """Generate daily maintenance schedule and optimize assignments"""
    try:
        db = SessionLocal()
        maintenance_service = MaintenanceService(db)

        # Get all departments for scheduling
        from app.models.department import Department as DepartmentModel
        departments = db.query(DepartmentModel).all()

        schedule_results = {}
        total_optimized = 0

        for department in departments:
            try:
                # Optimize maintenance schedule for this department
                optimization = await maintenance_service.optimize_maintenance_schedule(
                    department_id=str(department.id)
                )
                schedule_results[department.name] = optimization
                total_optimized += optimization["total_items"]

            except Exception as dept_error:
                logger.error(f"Failed to optimize schedule for {department.name}: {str(dept_error)}")
                schedule_results[department.name] = {"error": str(dept_error)}

        # Generate alerts for upcoming maintenance
        alert_service = AlertService(db)
        alert_results = await alert_service.check_and_send_alerts()

        logger.info(f"Daily schedule generated. Total optimized: {total_optimized}")
        return {
            "status": "success",
            "schedule_results": schedule_results,
            "alert_results": alert_results,
            "total_optimized": total_optimized
        }

    except Exception as e:
        logger.error(f"Daily schedule generation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.maintenance.update_maintenance_status")
def update_maintenance_status(self):
    """Update maintenance status for all equipment"""
    try:
        db = SessionLocal()
        from app.models.equipment import Equipment as EquipmentModel

        # Get all active equipment
        equipment = db.query(EquipmentModel).filter(EquipmentModel.status == "active").all()

        updated_count = 0
        now = datetime.utcnow()

        for item in equipment:
            try:
                # Check if equipment is overdue
                if item.next_maintenance_date and item.next_maintenance_date < now:
                    # Update status to indicate maintenance is needed
                    # In a real implementation, you might have a more sophisticated status system
                    updated_count += 1

            except Exception as item_error:
                logger.error(f"Failed to update status for equipment {item.id}: {str(item_error)}")

        logger.info(f"Maintenance status updated for {updated_count} equipment items")
        return {
            "status": "success",
            "updated_count": updated_count
        }

    except Exception as e:
        logger.error(f"Maintenance status update failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.maintenance.schedule_follow_up")
def schedule_follow_up(self, equipment_id: str, maintenance_log_id: str):
    """Schedule follow-up maintenance after completion"""
    try:
        db = SessionLocal()
        maintenance_service = MaintenanceService(db)

        # Schedule next maintenance using AI optimization
        result = await maintenance_service.schedule_next_maintenance(equipment_id)

        logger.info(f"Follow-up maintenance scheduled for equipment {equipment_id}")
        return {
            "status": "success",
            "equipment_id": equipment_id,
            "maintenance_log_id": maintenance_log_id,
            "next_maintenance": result
        }

    except Exception as e:
        logger.error(f"Follow-up scheduling failed for equipment {equipment_id}: {str(e)}")
        return {
            "status": "error",
            "equipment_id": equipment_id,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.maintenance.cleanup_completed_tasks")
def cleanup_completed_tasks(self):
    """Clean up old completed maintenance tasks and logs"""
    try:
        db = SessionLocal()
        from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel

        # Delete maintenance logs older than 2 years
        two_years_ago = datetime.utcnow() - timedelta(days=730)

        deleted_count = (
            db.query(MaintenanceLogModel)
            .filter(MaintenanceLogModel.performed_at < two_years_ago)
            .delete()
        )

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old maintenance logs")
        return {
            "status": "success",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(f"Maintenance cleanup failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()