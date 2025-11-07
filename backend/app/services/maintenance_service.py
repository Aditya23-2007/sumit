from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.equipment import Equipment as EquipmentModel
from app.models.maintenance_log import MaintenanceLog as MaintenanceLogModel
from app.models.maintenance_task import MaintenanceTask as MaintenanceTaskModel
from app.models.department import Department as DepartmentModel
from app.services.ai_service import AIService
import logging

logger = logging.getLogger(__name__)


class MaintenanceService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()

    async def get_upcoming_maintenance(
        self,
        end_date: datetime,
        department_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming maintenance items within specified date range"""

        query = (
            self.db.query(
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
        )

        if department_id:
            query = query.filter(EquipmentModel.department_id == department_id)

        results = query.all()

        upcoming_maintenance = []
        for equipment, department_name in results:
            days_until = (equipment.next_maintenance_date - datetime.utcnow()).days

            # Get maintenance tasks for this equipment
            tasks = (
                self.db.query(MaintenanceTaskModel)
                .filter(MaintenanceTaskModel.equipment_id == equipment.id)
                .order_by(MaintenanceTaskModel.priority.desc())
                .all()
            )

            upcoming_maintenance.append({
                "equipment_id": str(equipment.id),
                "equipment_name": equipment.name,
                "department_name": department_name,
                "department_id": str(equipment.department_id),
                "next_maintenance_date": equipment.next_maintenance_date,
                "days_until_maintenance": days_until,
                "priority": self._calculate_maintenance_priority(days_until, equipment.maintenance_interval_months),
                "estimated_duration_hours": sum(task.estimated_duration_hours or 1 for task in tasks),
                "task_count": len(tasks),
                "last_maintenance_date": equipment.last_maintenance_date
            })

        return upcoming_maintenance

    async def get_overdue_maintenance(
        self,
        department_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get equipment with overdue maintenance"""

        query = (
            self.db.query(
                EquipmentModel,
                DepartmentModel.name.label("department_name")
            )
            .join(DepartmentModel)
            .filter(
                EquipmentModel.next_maintenance_date < datetime.utcnow(),
                EquipmentModel.status == "active"
            )
            .order_by(EquipmentModel.next_maintenance_date.asc())
        )

        if department_id:
            query = query.filter(EquipmentModel.department_id == department_id)

        results = query.all()

        overdue_maintenance = []
        for equipment, department_name in results:
            days_overdue = (datetime.utcnow() - equipment.next_maintenance_date).days

            overdue_maintenance.append({
                "equipment_id": str(equipment.id),
                "equipment_name": equipment.name,
                "department_name": department_name,
                "department_id": str(equipment.department_id),
                "due_date": equipment.next_maintenance_date,
                "days_overdue": days_overdue,
                "priority": self._calculate_overdue_priority(days_overdue),
                "last_maintenance_date": equipment.last_maintenance_date
            })

        return overdue_maintenance

    async def get_user_maintenance_tasks(
        self,
        user_id: str,
        department_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get maintenance tasks assigned to a user based on their department"""

        # Get upcoming maintenance for user's department
        end_date = datetime.utcnow() + timedelta(days=30)
        upcoming = await self.get_upcoming_maintenance(end_date, department_id)

        user_tasks = []
        for maintenance_item in upcoming:
            # Get detailed tasks for this equipment
            tasks = (
                self.db.query(MaintenanceTaskModel)
                .filter(MaintenanceTaskModel.equipment_id == maintenance_item["equipment_id"])
                .order_by(MaintenanceTaskModel.priority.desc())
                .all()
            )

            for task in tasks:
                user_tasks.append({
                    "task_id": str(task.id),
                    "task_name": task.task_name,
                    "task_description": task.task_description,
                    "equipment_id": maintenance_item["equipment_id"],
                    "equipment_name": maintenance_item["equipment_name"],
                    "department_name": maintenance_item["department_name"],
                    "priority": task.priority.value,
                    "estimated_duration_hours": task.estimated_duration_hours,
                    "required_tools": task.required_tools or [],
                    "scheduled_date": maintenance_item["next_maintenance_date"],
                    "days_until_maintenance": maintenance_item["days_until_maintenance"]
                })

        # Sort by priority and due date
        user_tasks.sort(key=lambda x: (
            self._priority_sort_order(x["priority"]),
            x["days_until_maintenance"]
        ))

        return user_tasks

    async def schedule_next_maintenance(self, equipment_id: str) -> Dict[str, Any]:
        """Schedule next maintenance after completion and optimize using AI"""

        equipment = self.db.query(EquipmentModel).filter(EquipmentModel.id == equipment_id).first()
        if not equipment:
            raise ValueError("Equipment not found")

        # Get maintenance history for AI prediction
        maintenance_history = (
            self.db.query(MaintenanceLogModel)
            .filter(MaintenanceLogModel.equipment_id == equipment_id)
            .order_by(MaintenanceLogModel.performed_at.desc())
            .limit(10)
            .all()
        )

        history_data = []
        for log in maintenance_history:
            history_data.append({
                "performed_at": log.performed_at.isoformat(),
                "tasks_completed": log.tasks_completed,
                "duration_hours": log.duration_hours,
                "notes": log.notes
            })

        # Get equipment details for AI
        equipment_details = {
            "name": equipment.name,
            "description": equipment.description,
            "maintenance_interval_months": equipment.maintenance_interval_months,
            "last_maintenance_date": equipment.last_maintenance_date.isoformat() if equipment.last_maintenance_date else None
        }

        try:
            # Use AI to predict optimal next maintenance date
            ai_prediction = await self.ai_service.get_maintenance_prediction(
                equipment_id=equipment_id,
                maintenance_history=history_data,
                equipment_details=equipment_details
            )

            # Calculate next maintenance date based on AI prediction
            base_interval = equipment.maintenance_interval_months or 6
            adjustment_factor = self._get_ai_adjustment_factor(ai_prediction)

            adjusted_months = int(base_interval * adjustment_factor)
            next_maintenance_date = datetime.utcnow() + timedelta(days=adjusted_months * 30)

            # Update equipment next maintenance date
            equipment.next_maintenance_date = next_maintenance_date
            self.db.commit()

            logger.info(f"Scheduled next maintenance for {equipment.name} on {next_maintenance_date}")

            return {
                "equipment_id": equipment_id,
                "next_maintenance_date": next_maintenance_date,
                "ai_prediction": ai_prediction,
                "adjusted_interval_months": adjusted_months
            }

        except Exception as e:
            logger.error(f"Failed to schedule AI-driven maintenance for {equipment.name}: {str(e)}")
            # Fallback to standard scheduling
            standard_interval = equipment.maintenance_interval_months or 6
            standard_next_date = datetime.utcnow() + timedelta(days=standard_interval * 30)

            equipment.next_maintenance_date = standard_next_date
            self.db.commit()

            return {
                "equipment_id": equipment_id,
                "next_maintenance_date": standard_next_date,
                "ai_prediction": None,
                "adjusted_interval_months": standard_interval
            }

    def _calculate_maintenance_priority(
        self,
        days_until: int,
        interval_months: int
    ) -> str:
        """Calculate maintenance priority based on urgency and equipment characteristics"""

        if days_until <= 7:
            return "critical"
        elif days_until <= 14:
            return "high"
        elif days_until <= 30:
            return "medium"
        else:
            return "low"

    def _calculate_overdue_priority(self, days_overdue: int) -> str:
        """Calculate priority for overdue maintenance"""

        if days_overdue >= 30:
            return "critical"
        elif days_overdue >= 14:
            return "high"
        elif days_overdue >= 7:
            return "medium"
        else:
            return "low"

    def _priority_sort_order(self, priority: str) -> int:
        """Convert priority to sort order (lower number = higher priority)"""
        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3
        }
        return priority_order.get(priority, 3)

    def _get_ai_adjustment_factor(self, ai_prediction: Dict[str, Any]) -> float:
        """Get maintenance interval adjustment factor based on AI prediction"""

        breakdown_probability = ai_prediction.get("breakdown_probability", 10)
        recommended_priority = ai_prediction.get("recommended_priority", "medium")

        # Base adjustment factors
        priority_factors = {
            "critical": 0.7,  # Shorten interval by 30%
            "high": 0.85,     # Shorten interval by 15%
            "medium": 1.0,    # Keep standard interval
            "low": 1.2        # Extend interval by 20%
        }

        base_factor = priority_factors.get(recommended_priority, 1.0)

        # Additional adjustment based on breakdown probability
        if breakdown_probability >= 70:
            base_factor *= 0.6  # Significant reduction
        elif breakdown_probability >= 50:
            base_factor *= 0.8  # Moderate reduction
        elif breakdown_probability >= 30:
            base_factor *= 0.9  # Slight reduction
        elif breakdown_probability <= 10:
            base_factor *= 1.1  # Slight extension

        # Ensure the factor is within reasonable bounds
        return max(0.5, min(1.5, base_factor))

    async def optimize_maintenance_schedule(
        self,
        department_id: Optional[str] = None,
        technician_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimize maintenance schedule using AI and resource allocation"""

        # Get upcoming maintenance items
        end_date = datetime.utcnow() + timedelta(days=60)
        upcoming_maintenance = await self.get_upcoming_maintenance(end_date, department_id)

        # Group maintenance by department and location for optimization
        optimized_schedule = self._group_maintenance_by_proximity(upcoming_maintenance)

        # Calculate resource requirements
        total_time_required = sum(item["estimated_duration_hours"] for item in upcoming_maintenance)
        average_daily_capacity = 8  # 8 hours per day per technician

        optimization_results = {
            "total_items": len(upcoming_maintenance),
            "total_hours_required": total_time_required,
            "estimated_days_required": total_time_required / average_daily_capacity,
            "optimized_groups": optimized_schedule,
            "recommendations": self._generate_optimization_recommendations(upcoming_maintenance)
        }

        return optimization_results

    def _group_maintenance_by_proximity(self, maintenance_items: List[Dict]) -> List[Dict]:
        """Group maintenance items by department for efficient scheduling"""

        groups = {}
        for item in maintenance_items:
            department = item["department_name"]
            if department not in groups:
                groups[department] = {
                    "department_name": department,
                    "department_id": item["department_id"],
                    "items": [],
                    "total_duration": 0,
                    "earliest_date": None,
                    "latest_date": None
                }

            groups[department]["items"].append(item)
            groups[department]["total_duration"] += item["estimated_duration_hours"]

            # Update date range
            if not groups[department]["earliest_date"] or item["next_maintenance_date"] < groups[department]["earliest_date"]:
                groups[department]["earliest_date"] = item["next_maintenance_date"]
            if not groups[department]["latest_date"] or item["next_maintenance_date"] > groups[department]["latest_date"]:
                groups[department]["latest_date"] = item["next_maintenance_date"]

        return list(groups.values())

    def _generate_optimization_recommendations(self, maintenance_items: List[Dict]) -> List[str]:
        """Generate optimization recommendations based on maintenance data"""

        recommendations = []

        # Analyze overdue items
        overdue_count = len([item for item in maintenance_items if item["days_until_maintenance"] < 0])
        if overdue_count > 0:
            recommendations.append(f"Priority: {overdue_count} items are overdue and require immediate attention")

        # Analyze high-priority items
        high_priority_count = len([item for item in maintenance_items if item["priority"] in ["critical", "high"]])
        if high_priority_count > 5:
            recommendations.append("Consider scheduling additional resources for high-priority maintenance items")

        # Analyze workload distribution
        total_hours = sum(item["estimated_duration_hours"] for item in maintenance_items)
        if total_hours > 40:  # More than 1 week of work
            recommendations.append("Workload exceeds 1 week capacity. Consider staggered scheduling")

        # Department-specific recommendations
        departments = {}
        for item in maintenance_items:
            dept = item["department_name"]
            if dept not in departments:
                departments[dept] = 0
            departments[dept] += 1

        if len(departments) > 1:
            busiest_dept = max(departments, key=departments.get)
            recommendations.append(f"Consider dedicating specific days to {busiest_dept} department for efficiency")

        return recommendations