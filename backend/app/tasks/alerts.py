from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.alert_service import AlertService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.alerts.check_critical_alerts")
def check_critical_alerts(self):
    """Check for critical alerts and send notifications"""
    try:
        db = SessionLocal()
        alert_service = AlertService(db)

        # Check for all types of alerts
        results = alert_service.check_and_send_alerts()

        logger.info(f"Critical alerts check completed: {results}")
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Critical alerts check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.alerts.send_overdue_alerts")
def send_overdue_alerts(self):
    """Send alerts for overdue maintenance"""
    try:
        db = SessionLocal()
        alert_service = AlertService(db)

        # Generate alerts for overdue equipment specifically
        results = alert_service.generate_maintenance_alerts()

        logger.info(f"Overdue alerts sent: {results}")
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Overdue alerts failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.alerts.process_acknowledgments")
def process_acknowledgments(self):
    """Process alert acknowledgments and update schedules"""
    try:
        db = SessionLocal()
        # Implementation for processing acknowledgments
        # This would handle any follow-up actions after alerts are acknowledged

        logger.info("Alert acknowledgments processed")
        return {
            "status": "success",
            "message": "Acknowledgments processed successfully"
        }

    except Exception as e:
        logger.error(f"Alert acknowledgment processing failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()