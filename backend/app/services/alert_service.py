from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.equipment import Equipment as EquipmentModel
from app.models.maintenance_alert import MaintenanceAlert as MaintenanceAlertModel, AlertType
from app.models.department import Department as DepartmentModel
from app.models.user import User as UserModel
from app.services.email_service import EmailService
from app.services.ai_service import AIService
import logging

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.ai_service = AIService()

    async def generate_maintenance_alerts(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate maintenance alerts for due and overdue equipment"""

        # Get equipment that needs alerts
        equipment_needing_alerts = await self._get_equipment_needing_alerts(department_id)

        alerts_created = 0
        alerts_skipped = 0
        errors = []

        for equipment, department_name in equipment_needing_alerts:
            try:
                # Check if alert already exists for this equipment and type
                existing_alert = (
                    self.db.query(MaintenanceAlertModel)
                    .filter(
                        MaintenanceAlertModel.equipment_id == equipment.id,
                        MaintenanceAlertModel.acknowledged_at.is_(None)
                    )
                    .first()
                )

                if existing_alert:
                    alerts_skipped += 1
                    continue

                # Determine alert type and create alert
                alert_data = await self._determine_alert_type(equipment)
                alert = MaintenanceAlertModel(
                    equipment_id=equipment.id,
                    alert_type=alert_data["alert_type"],
                    message=alert_data["message"],
                    scheduled_date=equipment.next_maintenance_date
                )

                self.db.add(alert)
                self.db.commit()

                # Send email notification
                await self._send_alert_notification(alert, equipment, department_name)

                alerts_created += 1

            except Exception as e:
                errors.append(f"Failed to create alert for {equipment.name}: {str(e)}")
                logger.error(f"Alert generation failed for {equipment.name}: {str(e)}")

        return {
            "alerts_created": alerts_created,
            "alerts_skipped": alerts_skipped,
            "errors": errors,
            "total_processed": len(equipment_needing_alerts)
        }

    async def generate_predictive_failure_alerts(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate alerts based on AI predictions for equipment failures"""

        # Get equipment with maintenance history for AI analysis
        equipment_for_analysis = await self._get_equipment_for_predictive_analysis(department_id)

        predictive_alerts_created = 0
        errors = []

        for equipment, department_name in equipment_for_analysis:
            try:
                # Get maintenance history
                maintenance_history = await self._get_maintenance_history(equipment.id)

                if not maintenance_history:
                    continue  # Skip equipment with no history

                # Get AI prediction
                equipment_details = {
                    "name": equipment.name,
                    "description": equipment.description,
                    "maintenance_interval_months": equipment.maintenance_interval_months
                }

                ai_prediction = await self.ai_service.get_maintenance_prediction(
                    equipment_id=str(equipment.id),
                    maintenance_history=maintenance_history,
                    equipment_details=equipment_details
                )

                # Check if prediction warrants an alert
                if ai_prediction["breakdown_probability"] >= 50:  # 50% threshold
                    await self._create_predictive_alert(
                        equipment, department_name, ai_prediction
                    )
                    predictive_alerts_created += 1

            except Exception as e:
                errors.append(f"Failed to analyze {equipment.name} for predictive alerts: {str(e)}")
                logger.error(f"Predictive alert analysis failed for {equipment.name}: {str(e)}")

        return {
            "predictive_alerts_created": predictive_alerts_created,
            "errors": errors,
            "total_analyzed": len(equipment_for_analysis)
        }

    async def check_and_send_alerts(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        """Main method to check all conditions and send appropriate alerts"""

        results = {
            "maintenance_alerts": {},
            "predictive_alerts": {},
            "summary": {
                "total_alerts_created": 0,
                "total_errors": 0
            }
        }

        try:
            # Generate standard maintenance alerts
            maintenance_results = await self.generate_maintenance_alerts(department_id)
            results["maintenance_alerts"] = maintenance_results
            results["summary"]["total_alerts_created"] += maintenance_results["alerts_created"]
            results["summary"]["total_errors"] += len(maintenance_results["errors"])

            # Generate predictive failure alerts
            predictive_results = await self.generate_predictive_failure_alerts(department_id)
            results["predictive_alerts"] = predictive_results
            results["summary"]["total_alerts_created"] += predictive_results["predictive_alerts_created"]
            results["summary"]["total_errors"] += len(predictive_results["errors"])

            logger.info(f"Alert generation completed. Total alerts created: {results['summary']['total_alerts_created']}")

        except Exception as e:
            logger.error(f"Alert checking process failed: {str(e)}")
            results["summary"]["total_errors"] += 1

        return results

    async def send_test_alert(self, recipient_email: str) -> Dict[str, Any]:
        """Send a test alert to verify email functionality"""

        try:
            test_alert_data = {
                "subject": "Test Alert - Predictive Maintenance System",
                "equipment_name": "Test Equipment",
                "alert_type": "due_soon",
                "message": "This is a test alert to verify the predictive maintenance system is working correctly.",
                "scheduled_date": datetime.utcnow() + timedelta(days=7),
                "department_name": "Test Department"
            }

            await self.email_service.send_maintenance_alert(
                recipient_email=recipient_email,
                alert_data=test_alert_data
            )

            return {
                "success": True,
                "message": "Test alert sent successfully",
                "recipient": recipient_email
            }

        except Exception as e:
            logger.error(f"Test alert failed: {str(e)}")
            return {
                "success": False,
                "message": f"Test alert failed: {str(e)}",
                "recipient": recipient_email
            }

    async def _get_equipment_needing_alerts(self, department_id: Optional[str] = None) -> List:
        """Get equipment that needs maintenance alerts"""

        thirty_days_from_now = datetime.utcnow() + timedelta(days=30)

        query = (
            self.db.query(
                EquipmentModel,
                DepartmentModel.name.label("department_name")
            )
            .join(DepartmentModel)
            .filter(
                EquipmentModel.next_maintenance_date <= thirty_days_from_now,
                EquipmentModel.status == "active",
                EquipmentModel.next_maintenance_date >= datetime.utcnow() - timedelta(days=1)  # Recently due or upcoming
            )
            .order_by(EquipmentModel.next_maintenance_date.asc())
        )

        if department_id:
            query = query.filter(EquipmentModel.department_id == department_id)

        return query.all()

    async def _get_equipment_for_predictive_analysis(self, department_id: Optional[str] = None) -> List:
        """Get equipment with sufficient history for predictive analysis"""

        query = (
            self.db.query(
                EquipmentModel,
                DepartmentModel.name.label("department_name")
            )
            .join(DepartmentModel)
            .filter(
                EquipmentModel.status == "active",
                EquipmentModel.maintenance_interval_months.isnot(None)
            )
        )

        if department_id:
            query = query.filter(EquipmentModel.department_id == department_id)

        return query.all()

    async def _get_maintenance_history(self, equipment_id: str) -> List[Dict]:
        """Get maintenance history for equipment"""

        from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel

        logs = (
            self.db.query(MaintenanceLogModel)
            .filter(MaintenanceLogModel.equipment_id == equipment_id)
            .order_by(MaintenanceLogModel.performed_at.desc())
            .limit(10)
            .all()
        )

        history = []
        for log in logs:
            history.append({
                "performed_at": log.performed_at.isoformat(),
                "tasks_completed": log.tasks_completed,
                "duration_hours": log.duration_hours,
                "notes": log.notes
            })

        return history

    async def _determine_alert_type(self, equipment: EquipmentModel) -> Dict[str, Any]:
        """Determine alert type and message based on equipment status"""

        now = datetime.utcnow()
        days_until_due = (equipment.next_maintenance_date - now).days

        if days_until_due < 0:
            return {
                "alert_type": AlertType.overdue,
                "message": f"Maintenance for {equipment.name} is {abs(days_until_due)} days overdue. Immediate attention required."
            }
        elif days_until_due <= 7:
            return {
                "alert_type": AlertType.due_soon,
                "message": f"Maintenance for {equipment.name} is due in {days_until_due} days. Please schedule maintenance."
            }
        else:
            return {
                "alert_type": AlertType.due_soon,
                "message": f"Maintenance for {equipment.name} is scheduled for {equipment.next_maintenance_date.strftime('%B %d, %Y')}."
            }

    async def _create_predictive_alert(
        self,
        equipment: EquipmentModel,
        department_name: str,
        ai_prediction: Dict[str, Any]
    ) -> None:
        """Create a predictive failure alert based on AI analysis"""

        # Check if predictive alert already exists
        existing_alert = (
            self.db.query(MaintenanceAlertModel)
            .filter(
                MaintenanceAlertModel.equipment_id == equipment.id,
                MaintenanceAlertModel.alert_type == AlertType.predicted_failure,
                MaintenanceAlertModel.acknowledged_at.is_(None)
            )
            .first()
        )

        if existing_alert:
            return  # Skip if alert already exists

        # Create new predictive alert
        probability = ai_prediction["breakdown_probability"]
        additional_tasks = ai_prediction.get("additional_tasks", [])

        message = (
            f"AI analysis predicts {probability}% probability of equipment failure for {equipment.name}. "
            f"Recommended actions: {', '.join(additional_tasks) if additional_tasks else 'Schedule immediate inspection.'}"
        )

        alert = MaintenanceAlertModel(
            equipment_id=equipment.id,
            alert_type=AlertType.predicted_failure,
            message=message,
            scheduled_date=datetime.utcnow() + timedelta(days=1)  # Schedule for tomorrow
        )

        self.db.add(alert)
        self.db.commit()

        # Send email notification
        await self._send_alert_notification(alert, equipment, department_name, ai_prediction)

    async def _send_alert_notification(
        self,
        alert: MaintenanceAlertModel,
        equipment: EquipmentModel,
        department_name: str,
        ai_prediction: Optional[Dict] = None
    ) -> None:
        """Send email notification for alert"""

        try:
            # Get users to notify based on department
            users_to_notify = (
                self.db.query(UserModel)
                .filter(
                    UserModel.department_id == equipment.department_id,
                    UserModel.role.in_(["admin", "technician"])
                )
                .all()
            )

            alert_data = {
                "subject": f"Maintenance Alert: {alert.alert_type.value.upper()} - {equipment.name}",
                "equipment_name": equipment.name,
                "alert_type": alert.alert_type.value,
                "message": alert.message,
                "scheduled_date": alert.scheduled_date,
                "department_name": department_name,
                "ai_prediction": ai_prediction
            }

            for user in users_to_notify:
                await self.email_service.send_maintenance_alert(
                    recipient_email=user.email,
                    alert_data=alert_data
                )

        except Exception as e:
            logger.error(f"Failed to send alert notification for {equipment.name}: {str(e)}")

    async def get_alert_statistics(self, department_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about alerts for dashboard"""

        base_query = self.db.query(MaintenanceAlertModel)

        if department_id:
            # Filter by department
            equipment_ids = (
                self.db.query(EquipmentModel.id)
                .filter(EquipmentModel.department_id == department_id)
                .subquery()
            )
            base_query = base_query.filter(MaintenanceAlertModel.equipment_id.in_(equipment_ids))

        # Total alerts
        total_alerts = base_query.count()

        # Unacknowledged alerts
        unacknowledged = base_query.filter(MaintenanceAlertModel.acknowledged_at.is_(None)).count()

        # Alerts by type
        alerts_by_type = {}
        for alert_type in AlertType:
            count = base_query.filter(MaintenanceAlertModel.alert_type == alert_type).count()
            alerts_by_type[alert_type.value] = count

        # Recent alerts (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_alerts = base_query.filter(MaintenanceAlertModel.created_at >= seven_days_ago).count()

        return {
            "total_alerts": total_alerts,
            "unacknowledged_alerts": unacknowledged,
            "alerts_by_type": alerts_by_type,
            "recent_alerts_7_days": recent_alerts,
            "acknowledgment_rate": ((total_alerts - unacknowledged) / total_alerts * 100) if total_alerts > 0 else 100
        }