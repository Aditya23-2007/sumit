from celery import Celery
from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "predictive_maintenance",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configure task schedules
celery_app.conf.beat_schedule = {
    # Check for critical alerts every hour
    "check-critical-alerts": {
        "task": "app.tasks.alerts.check_critical_alerts",
        "schedule": 3600.0,  # 1 hour
    },

    # Generate daily maintenance schedule
    "generate-daily-schedule": {
        "task": "app.tasks.maintenance.generate_daily_schedule",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "daily"},
    },

    # Check for predictive maintenance opportunities
    "predictive-analysis": {
        "task": "app.tasks.ai.predictive_analysis",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "ai"},
    },

    # Weekly maintenance report
    "weekly-report": {
        "task": "app.tasks.reports.generate_weekly_report",
        "schedule": 604800.0,  # 7 days
        "options": {"queue": "reports"},
    },

    # Monthly analytics report
    "monthly-analytics": {
        "task": "app.tasks.analytics.generate_monthly_analytics",
        "schedule": 2592000.0,  # 30 days
        "options": {"queue": "analytics"},
    },

    # Database backup and cleanup
    "database-maintenance": {
        "task": "app.tasks.system.database_maintenance",
        "schedule": 86400.0,  # 24 hours
        "options": {"queue": "system"},
    }
}

# Import tasks to register them
from app.tasks import alerts, maintenance, ai, reports, analytics, system