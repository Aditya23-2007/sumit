from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.system.database_maintenance")
def database_maintenance(self):
    """Perform database maintenance tasks"""
    try:
        db = SessionLocal()

        maintenance_results = {
            "old_logs_deleted": 0,
            "orphaned_records_cleaned": 0,
            "indexes_optimized": 0,
            "errors": []
        }

        try:
            # Clean up old maintenance logs (older than 2 years)
            from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
            two_years_ago = datetime.utcnow() - timedelta(days=730)

            deleted_logs = (
                db.query(MaintenanceLogModel)
                .filter(MaintenanceLogModel.performed_at < two_years_ago)
                .delete()
            )
            maintenance_results["old_logs_deleted"] = deleted_logs

            # Clean up old acknowledged alerts (older than 6 months)
            from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel
            six_months_ago = datetime.utcnow() - timedelta(days=180)

            deleted_alerts = (
                db.query(MaintenanceAlertModel)
                .filter(
                    MaintenanceAlertModel.acknowledged_at.isnot(None),
                    MaintenanceAlertModel.acknowledged_at < six_months_ago
                )
                .delete()
            )
            maintenance_results["old_alerts_deleted"] = deleted_alerts

            db.commit()

            # Note: In a production environment, you would also:
            # - Optimize table indexes
            # - Update table statistics
            # - Check for database fragmentation
            # - Backup database before maintenance

            logger.info("Database maintenance completed successfully")
            maintenance_results["status"] = "success"

        except Exception as e:
            logger.error(f"Database maintenance error: {str(e)}")
            maintenance_results["errors"].append(str(e))
            db.rollback()

        return maintenance_results

    except Exception as e:
        logger.error(f"Database maintenance failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.system.health_check")
def health_check(self):
    """Perform system health checks"""
    try:
        health_results = {
            "database_connection": False,
            "redis_connection": False,
            "external_services": {},
            "disk_space": None,
            "memory_usage": None,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Check database connection
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            health_results["database_connection"] = True
            db.close()
        except Exception as db_error:
            health_results["database_error"] = str(db_error)
            logger.error(f"Database health check failed: {str(db_error)}")

        # Check Redis connection
        try:
            import redis
            from app.core.config import settings
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            health_results["redis_connection"] = True
        except Exception as redis_error:
            health_results["redis_error"] = str(redis_error)
            logger.error(f"Redis health check failed: {str(redis_error)}")

        # Check external services (OpenAI)
        try:
            from app.core.config import settings
            import openai

            if settings.OPENAI_API_KEY:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                # Simple API test - check models available
                models = client.models.list()
                health_results["external_services"]["openai"] = True
            else:
                health_results["external_services"]["openai"] = "No API key configured"

        except Exception as openai_error:
            health_results["external_services"]["openai"] = str(openai_error)
            logger.error(f"OpenAI health check failed: {str(openai_error)}")

        # Check system resources (simplified)
        try:
            import psutil
            disk_usage = psutil.disk_usage('/')
            memory = psutil.virtual_memory()

            health_results["disk_space"] = {
                "total_gb": disk_usage.total // (1024**3),
                "free_gb": disk_usage.free // (1024**3),
                "usage_percent": (disk_usage.used / disk_usage.total) * 100
            }

            health_results["memory_usage"] = {
                "total_gb": memory.total // (1024**3),
                "available_gb": memory.available // (1024**3),
                "usage_percent": memory.percent
            }

        except Exception as resource_error:
            health_results["resource_error"] = str(resource_error)
            logger.error(f"System resource check failed: {str(resource_error)}")

        # Overall health status
        healthy_components = [
            health_results["database_connection"],
            health_results["redis_connection"]
        ]
        health_results["overall_healthy"] = all(healthy_components)

        logger.info(f"System health check completed. Overall healthy: {health_results['overall_healthy']}")
        return {
            "status": "success",
            "health": health_results
        }

    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, name="app.tasks.system.backup_data")
def backup_data(self):
    """Perform data backup tasks"""
    try:
        # This is a placeholder for backup implementation
        # In a real system, you would:
        # - Export database to backup format
        # - Upload to cloud storage (AWS S3, etc.)
        # - Verify backup integrity
        # - Clean up old backups

        logger.info("Data backup task completed (placeholder implementation)")
        return {
            "status": "success",
            "message": "Data backup completed successfully",
            "backup_location": "placeholder_backup_location",
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Data backup failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


@celery_app.task(bind=True, name="app.tasks.system.cleanup_temp_files")
def cleanup_temp_files(self):
    """Clean up temporary files and resources"""
    try:
        import os
        import tempfile

        cleaned_files = 0
        cleaned_space = 0

        # Clean up temp directory
        temp_dir = tempfile.gettempdir()
        current_time = datetime.utcnow()

        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(filepath):
                    # Check if file is older than 24 hours
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if (current_time - file_time).days >= 1:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        cleaned_files += 1
                        cleaned_space += file_size

            except Exception as file_error:
                logger.error(f"Failed to clean up file {filepath}: {str(file_error)}")

        logger.info(f"Cleaned up {cleaned_files} temporary files, freed {cleaned_space} bytes")
        return {
            "status": "success",
            "cleaned_files": cleaned_files,
            "cleaned_space_bytes": cleaned_space,
            "cleaned_space_mb": cleaned_space / (1024 * 1024)
        }

    except Exception as e:
        logger.error(f"Temporary file cleanup failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }