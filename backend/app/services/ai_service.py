from typing import Dict, List, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.maintenance_task import TaskPriority
import logging

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def analyze_equipment(
        self,
        equipment_name: str,
        department_name: str,
        equipment_type: str = None
    ) -> Dict[str, Any]:
        """Analyze equipment and generate maintenance recommendations using AI"""

        prompt = f"""
        As an expert maintenance engineer, analyze the following equipment and provide comprehensive maintenance recommendations:

        Equipment Name: {equipment_name}
        Department: {department_name}
        Equipment Type: {equipment_type or 'Not specified'}

        Please provide:
        1. A detailed description of this equipment type and its typical function
        2. Recommended maintenance interval in months (consider usage in {department_name})
        3. A list of specific maintenance tasks with priorities
        4. Estimated duration for each task
        5. Required tools for each task

        Format your response as JSON with the following structure:
        {{
            "description": "Detailed equipment description",
            "maintenance_interval_months": integer,
            "maintenance_tasks": [
                {{
                    "name": "Task name",
                    "description": "Task description",
                    "priority": "low|medium|high|critical",
                    "estimated_duration_hours": integer,
                    "required_tools": ["tool1", "tool2"]
                }}
            ]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert maintenance engineer providing equipment analysis and maintenance recommendations. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            content = response.choices[0].message.content
            logger.info(f"AI analysis completed for equipment: {equipment_name}")

            # Parse JSON response
            import json
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                logger.warning(f"Failed to parse AI response as JSON: {content}")
                result = self._get_fallback_analysis(equipment_name, department_name)

            # Validate and sanitize the result
            return self._validate_ai_result(result)

        except Exception as e:
            logger.error(f"AI analysis failed for equipment {equipment_name}: {str(e)}")
            return self._get_fallback_analysis(equipment_name, department_name)

    def _validate_ai_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize AI results"""
        validated_result = {
            "description": result.get("description", "Equipment analysis not available"),
            "maintenance_interval_months": min(max(result.get("maintenance_interval_months", 6), 1), 24),  # Between 1-24 months
            "maintenance_tasks": []
        }

        # Validate maintenance tasks
        tasks = result.get("maintenance_tasks", [])
        for task in tasks[:10]:  # Limit to 10 tasks max
            validated_task = {
                "name": task.get("name", "Unknown Task")[:100],  # Limit name length
                "description": task.get("description", "Task description not available")[:500],
                "priority": self._validate_priority(task.get("priority", "medium")),
                "estimated_duration_hours": min(max(task.get("estimated_duration_hours", 1), 1), 8),  # Between 1-8 hours
                "required_tools": [tool[:50] for tool in task.get("required_tools", [])[:5]]  # Limit tools
            }
            validated_result["maintenance_tasks"].append(validated_task)

        # Ensure at least one task
        if not validated_result["maintenance_tasks"]:
            validated_result["maintenance_tasks"].append({
                "name": "General Inspection",
                "description": "Perform general inspection and basic maintenance tasks",
                "priority": TaskPriority.medium,
                "estimated_duration_hours": 2,
                "required_tools": ["Basic tool kit"]
            })

        return validated_result

    def _validate_priority(self, priority: str) -> TaskPriority:
        """Validate and normalize priority values"""
        priority_mapping = {
            "low": TaskPriority.low,
            "medium": TaskPriority.medium,
            "high": TaskPriority.high,
            "critical": TaskPriority.critical,
            "urgent": TaskPriority.critical,
            "important": TaskPriority.high,
            "normal": TaskPriority.medium,
            "routine": TaskPriority.low
        }

        return priority_mapping.get(priority.lower(), TaskPriority.medium)

    def _get_fallback_analysis(self, equipment_name: str, department_name: str) -> Dict[str, Any]:
        """Provide fallback analysis when AI service fails"""
        return {
            "description": f"{equipment_name} located in {department_name}. Standard equipment requiring regular maintenance to ensure optimal performance and safety.",
            "maintenance_interval_months": 6,
            "maintenance_tasks": [
                {
                    "name": "Visual Inspection",
                    "description": "Perform thorough visual inspection of equipment components",
                    "priority": TaskPriority.medium,
                    "estimated_duration_hours": 1,
                    "required_tools": ["Flashlight", "Safety equipment"]
                },
                {
                    "name": "Cleaning and Lubrication",
                    "description": "Clean equipment surfaces and lubricate moving parts",
                    "priority": TaskPriority.medium,
                    "estimated_duration_hours": 2,
                    "required_tools": ["Cleaning supplies", "Lubricants", "Cloths"]
                },
                {
                    "name": "Functional Test",
                    "description": "Test equipment functionality and performance",
                    "priority": TaskPriority.high,
                    "estimated_duration_hours": 1,
                    "required_tools": ["Testing equipment", "Safety equipment"]
                }
            ]
        }

    async def get_maintenance_prediction(
        self,
        equipment_id: str,
        maintenance_history: List[Dict],
        equipment_details: Dict
    ) -> Dict[str, Any]:
        """Predict maintenance needs based on historical data"""

        prompt = f"""
        Analyze the maintenance history and predict future maintenance needs for this equipment:

        Equipment Details: {equipment_details}
        Maintenance History: {maintenance_history[-5:]}  # Last 5 maintenance records

        Provide predictions for:
        1. Likelihood of breakdown in next 30 days (percentage)
        2. Recommended priority level for upcoming maintenance
        3. Any additional tasks needed based on history
        4. Risk factors to monitor

        Respond with JSON format:
        {{
            "breakdown_probability": percentage,
            "recommended_priority": "low|medium|high|critical",
            "additional_tasks": ["task1", "task2"],
            "risk_factors": ["factor1", "factor2"],
            "notes": "Additional insights"
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an AI predictive maintenance assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )

            content = response.choices[0].message.content
            import json
            result = json.loads(content)

            # Validate prediction result
            return self._validate_prediction_result(result)

        except Exception as e:
            logger.error(f"Prediction analysis failed: {str(e)}")
            return self._get_fallback_prediction()

    def _validate_prediction_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize prediction results"""
        return {
            "breakdown_probability": min(max(result.get("breakdown_probability", 10), 0), 100),
            "recommended_priority": self._validate_priority(result.get("recommended_priority", "medium")),
            "additional_tasks": [str(task)[:100] for task in result.get("additional_tasks", [])[:5]],
            "risk_factors": [str(factor)[:100] for factor in result.get("risk_factors", [])[:5]],
            "notes": result.get("notes", "No additional insights available")[:500]
        }

    def _get_fallback_prediction(self) -> Dict[str, Any]:
        """Provide fallback prediction when AI service fails"""
        return {
            "breakdown_probability": 15,
            "recommended_priority": TaskPriority.medium,
            "additional_tasks": ["Standard inspection procedures"],
            "risk_factors": ["Regular wear and tear"],
            "notes": "Continue with standard maintenance schedule"
        }