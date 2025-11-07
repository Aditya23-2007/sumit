from celery import current_app
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.ai_service import AIService
from app.services.alert_service import AlertService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.ai.predictive_analysis")
def predictive_analysis(self):
    """Run AI predictive analysis on all equipment"""
    try:
        db = SessionLocal()
        ai_service = AIService()
        alert_service = AlertService(db)

        # Get all equipment with maintenance history
        from app.models.equipment import Equipment as EquipmentModel
        equipment_list = db.query(EquipmentModel).filter(
            EquipmentModel.status == "active",
            EquipmentModel.maintenance_interval_months.isnot(None)
        ).all()

        analysis_results = {
            "total_analyzed": len(equipment_list),
            "predictions_generated": 0,
            "alerts_created": 0,
            "errors": []
        }

        for equipment in equipment_list:
            try:
                # Get maintenance history
                from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
                maintenance_history = (
                    db.query(MaintenanceLogModel)
                    .filter(MaintenanceLogModel.equipment_id == equipment.id)
                    .order_by(MaintenanceLogModel.performed_at.desc())
                    .limit(10)
                    .all()
                )

                if not maintenance_history:
                    continue  # Skip equipment with no history

                history_data = []
                for log in maintenance_history:
                    history_data.append({
                        "performed_at": log.performed_at.isoformat(),
                        "tasks_completed": log.tasks_completed,
                        "duration_hours": log.duration_hours,
                        "notes": log.notes
                    })

                # Get AI prediction
                equipment_details = {
                    "name": equipment.name,
                    "description": equipment.description,
                    "maintenance_interval_months": equipment.maintenance_interval_months
                }

                ai_prediction = await ai_service.get_maintenance_prediction(
                    equipment_id=str(equipment.id),
                    maintenance_history=history_data,
                    equipment_details=equipment_details
                )

                analysis_results["predictions_generated"] += 1

                # Create alerts for high-risk equipment
                if ai_prediction["breakdown_probability"] >= 50:
                    from app.models.department import Department as DepartmentModel
                    department = db.query(DepartmentModel).filter(DepartmentModel.id == equipment.department_id).first()

                    await alert_service._create_predictive_alert(
                        equipment, department.name if department else "Unknown", ai_prediction
                    )
                    analysis_results["alerts_created"] += 1

                logger.info(f"AI analysis completed for {equipment.name}: {ai_prediction['breakdown_probability']}% risk")

            except Exception as equipment_error:
                error_msg = f"Failed to analyze {equipment.name}: {str(equipment_error)}"
                logger.error(error_msg)
                analysis_results["errors"].append(error_msg)

        logger.info(f"Predictive analysis completed. Analyzed: {analysis_results['total_analyzed']}, "
                   f"Predictions: {analysis_results['predictions_generated']}, Alerts: {analysis_results['alerts_created']}")

        return {
            "status": "success",
            "results": analysis_results
        }

    except Exception as e:
        logger.error(f"Predictive analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.ai.analyze_equipment")
def analyze_equipment(self, equipment_id: str):
    """Analyze specific equipment with AI"""
    try:
        db = SessionLocal()
        ai_service = AIService()

        # Get equipment details
        from app.models.equipment import Equipment as EquipmentModel
        from app.models.department import Department as DepartmentModel

        equipment = db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
        if not equipment:
            raise ValueError(f"Equipment {equipment_id} not found")

        department = db.query(DepartmentModel).filter(DepartmentModel.id == equipment.department_id).first()
        department_name = department.name if department else "Unknown"

        # Perform AI analysis
        ai_result = await ai_service.analyze_equipment(
            equipment_name=equipment.name,
            department_name=department_name,
            equipment_type=equipment.description
        )

        # Update equipment with AI results
        equipment.ai_generated_description = ai_result["description"]
        equipment.maintenance_interval_months = ai_result["maintenance_interval_months"]

        # Create maintenance tasks based on AI recommendations
        from app.models.maintenance_task import MaintenanceTask as MaintenanceTaskModel
        for task_data in ai_result["maintenance_tasks"]:
            task = MaintenanceTaskModel(
                equipment_id=equipment.id,
                task_name=task_data["name"],
                task_description=task_data["description"],
                priority=task_data["priority"],
                estimated_duration_hours=task_data.get("estimated_duration_hours"),
                required_tools=task_data.get("required_tools", [])
            )
            db.add(task)

        db.commit()

        logger.info(f"AI analysis completed for equipment {equipment.name}")
        return {
            "status": "success",
            "equipment_id": equipment_id,
            "ai_result": ai_result
        }

    except Exception as e:
        logger.error(f"AI analysis failed for equipment {equipment_id}: {str(e)}")
        return {
            "status": "error",
            "equipment_id": equipment_id,
            "error": str(e)
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="app.tasks.ai.batch_analyze")
def batch_analyze(self, equipment_ids: list):
    """Batch analyze multiple equipment items"""
    try:
        results = {
            "total_requested": len(equipment_ids),
            "successful": 0,
            "failed": 0,
            "equipment_results": {}
        }

        for equipment_id in equipment_ids:
            try:
                # Trigger individual analysis task
                result = analyze_equipment.delay(equipment_id)
                results["equipment_results"][equipment_id] = {
                    "task_id": result.id,
                    "status": "queued"
                }

            except Exception as e:
                results["equipment_results"][equipment_id] = {
                    "error": str(e),
                    "status": "failed"
                }
                results["failed"] += 1

        logger.info(f"Batch AI analysis queued for {len(equipment_ids)} equipment items")
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Batch AI analysis failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }