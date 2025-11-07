import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = settings.GMAIL_EMAIL

    async def send_maintenance_alert(
        self,
        recipient_email: str,
        alert_data: Dict[str, Any]
    ) -> bool:
        """Send maintenance alert email"""

        try:
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = alert_data["subject"]
            message["From"] = self.sender_email
            message["To"] = recipient_email

            # Create HTML content
            html_content = self._generate_alert_html(alert_data)

            # Create text content
            text_content = self._generate_alert_text(alert_data)

            # Attach both plain text and HTML versions
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")

            message.attach(text_part)
            message.attach(html_part)

            # Send email
            await self._send_email(message, recipient_email)

            logger.info(f"Maintenance alert sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance alert to {recipient_email}: {str(e)}")
            return False

    async def send_welcome_email(
        self,
        recipient_email: str,
        user_name: str,
        department_name: str
    ) -> bool:
        """Send welcome email to new users"""

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Welcome to Predictive Maintenance System"
            message["From"] = self.sender_email
            message["To"] = recipient_email

            html_content = self._generate_welcome_html(user_name, department_name)
            text_content = self._generate_welcome_text(user_name, department_name)

            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")

            message.attach(text_part)
            message.attach(html_part)

            await self._send_email(message, recipient_email)

            logger.info(f"Welcome email sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {recipient_email}: {str(e)}")
            return False

    async def send_maintenance_reminder(
        self,
        recipient_email: str,
        equipment_name: str,
        scheduled_date: datetime,
        tasks: list
    ) -> bool:
        """Send maintenance reminder email"""

        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = f"Maintenance Reminder: {equipment_name}"
            message["From"] = self.sender_email
            message["To"] = recipient_email

            reminder_data = {
                "equipment_name": equipment_name,
                "scheduled_date": scheduled_date,
                "tasks": tasks
            }

            html_content = self._generate_reminder_html(reminder_data)
            text_content = self._generate_reminder_text(reminder_data)

            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")

            message.attach(text_part)
            message.attach(html_part)

            await self._send_email(message, recipient_email)

            logger.info(f"Maintenance reminder sent to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send maintenance reminder to {recipient_email}: {str(e)}")
            return False

    async def _send_email(self, message: MIMEMultipart, recipient_email: str) -> None:
        """Send email using SMTP"""

        # Create secure connection
        context = ssl.create_default_context()

        # Connect to SMTP server and send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls(context=context)

            # Use Gmail API key for authentication if available
            if settings.GMAIL_API_KEY:
                # In a real implementation, you would use Gmail API
                # For now, we'll use basic SMTP (you'll need to enable less secure apps or use app passwords)
                server.login(self.sender_email, settings.GMAIL_API_KEY)
            else:
                logger.warning("No Gmail credentials configured, skipping email send")
                return

            server.sendmail(self.sender_email, recipient_email, message.as_string())

    def _generate_alert_html(self, alert_data: Dict[str, Any]) -> str:
        """Generate HTML content for maintenance alert"""

        urgency_color = {
            "overdue": "#dc3545",      # Red
            "predicted_failure": "#fd7e14",  # Orange
            "due_soon": "#ffc107",     # Yellow
            "info": "#17a2b8"          # Blue
        }

        color = urgency_color.get(alert_data["alert_type"], "#6c757d")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .alert-info {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid {color}; margin: 15px 0; }}
                .btn {{ display: inline-block; padding: 12px 24px; background-color: {color}; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔧 Maintenance Alert</h1>
                    <p>{alert_data["alert_type"].upper().replace("_", " ")}</p>
                </div>

                <div class="alert-info">
                    <h3>Equipment: {alert_data["equipment_name"]}</h3>
                    <p><strong>Department:</strong> {alert_data["department_name"]}</p>
                    <p><strong>Scheduled Date:</strong> {alert_data["scheduled_date"].strftime("%B %d, %Y") if alert_data["scheduled_date"] else "ASAP"}</p>
                    <p><strong>Message:</strong></p>
                    <p>{alert_data["message"]}</p>
                </div>

                {self._generate_ai_prediction_html(alert_data.get("ai_prediction")) if alert_data.get("ai_prediction") else ""}

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/dashboard" class="btn">
                        View Dashboard
                    </a>
                </div>

                <div class="footer">
                    <p>This is an automated message from the Predictive Maintenance System.</p>
                    <p>If you believe this was sent in error, please contact your system administrator.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_alert_text(self, alert_data: Dict[str, Any]) -> str:
        """Generate plain text content for maintenance alert"""

        text = f"""
MAINTENANCE ALERT - {alert_data["alert_type"].upper()}

Equipment: {alert_data["equipment_name"]}
Department: {alert_data["department_name"]}
Scheduled Date: {alert_data["scheduled_date"].strftime("%B %d, %Y") if alert_data["scheduled_date"] else "ASAP"}

Message:
{alert_data["message"]}

"""

        if alert_data.get("ai_prediction"):
            text += f"""
AI Prediction:
- Breakdown Probability: {alert_data["ai_prediction"]["breakdown_probability"]}%
- Recommended Priority: {alert_data["ai_prediction"]["recommended_priority"]}
- Additional Tasks: {", ".join(alert_data["ai_prediction"]["additional_tasks"])}

"""

        text += f"""
Please visit the dashboard to take action: {settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/dashboard

This is an automated message from the Predictive Maintenance System.
"""

        return text

    def _generate_welcome_html(self, user_name: str, department_name: str) -> str:
        """Generate HTML content for welcome email"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: #28a745; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; text-align: center; }}
                .feature {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .btn {{ display: inline-block; padding: 12px 24px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to Predictive Maintenance!</h1>
                </div>

                <h2>Hello {user_name}!</h2>
                <p>Welcome to the Predictive Maintenance System. Your account has been set up for the <strong>{department_name}</strong> department.</p>

                <h3>What you can do:</h3>
                <div class="feature">
                    <h4>🔍 Monitor Equipment</h4>
                    <p>View all equipment in your department and their maintenance status.</p>
                </div>
                <div class="feature">
                    <h4>📅 Schedule Maintenance</h4>
                    <p>Plan and schedule maintenance activities with AI-powered recommendations.</p>
                </div>
                <div class="feature">
                    <h4>🚨 Receive Alerts</h4>
                    <p>Get proactive notifications about upcoming maintenance and potential failures.</p>
                </div>
                <div class="feature">
                    <h4>📊 View Analytics</h4>
                    <p>Track maintenance performance and equipment health metrics.</p>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/dashboard" class="btn">
                        Go to Dashboard
                    </a>
                </div>

                <p>If you have any questions, please contact your system administrator.</p>
            </div>
        </body>
        </html>
        """

    def _generate_welcome_text(self, user_name: str, department_name: str) -> str:
        """Generate plain text content for welcome email"""

        return f"""
WELCOME TO PREDICTIVE MAINTENANCE SYSTEM

Hello {user_name}!

Welcome to the Predictive Maintenance System. Your account has been set up for the {department_name} department.

What you can do:
- Monitor Equipment: View all equipment in your department and their maintenance status
- Schedule Maintenance: Plan and schedule maintenance activities with AI-powered recommendations
- Receive Alerts: Get proactive notifications about upcoming maintenance and potential failures
- View Analytics: Track maintenance performance and equipment health metrics

Get started here: {settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/dashboard

If you have any questions, please contact your system administrator.
"""

    def _generate_reminder_html(self, reminder_data: Dict[str, Any]) -> str:
        """Generate HTML content for maintenance reminder"""

        tasks_html = ""
        for task in reminder_data["tasks"]:
            tasks_html += f"<li>{task}</li>"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background-color: #007bff; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .reminder-info {{ background-color: #d1ecf1; padding: 15px; border-left: 4px solid #007bff; margin: 15px 0; }}
                .task-list {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .btn {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📅 Maintenance Reminder</h1>
                </div>

                <div class="reminder-info">
                    <h3>Equipment: {reminder_data["equipment_name"]}</h3>
                    <p><strong>Scheduled Date:</strong> {reminder_data["scheduled_date"].strftime("%B %d, %Y at %I:%M %p")}</p>
                </div>

                <h4>Maintenance Tasks:</h4>
                <div class="task-list">
                    <ul>{tasks_html}</ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/maintenance" class="btn">
                        View Maintenance Schedule
                    </a>
                </div>
            </div>
        </body>
        </html>
        """

    def _generate_reminder_text(self, reminder_data: Dict[str, Any]) -> str:
        """Generate plain text content for maintenance reminder"""

        tasks_text = "\n".join([f"- {task}" for task in reminder_data["tasks"]])

        return f"""
MAINTENANCE REMINDER

Equipment: {reminder_data["equipment_name"]}
Scheduled Date: {reminder_data["scheduled_date"].strftime("%B %d, %Y at %I:%M %p")}

Maintenance Tasks:
{tasks_text}

View your maintenance schedule: {settings.NEXT_PUBLIC_API_URL or 'http://localhost:3000'}/maintenance
"""

    def _generate_ai_prediction_html(self, ai_prediction: Dict[str, Any]) -> str:
        """Generate HTML content for AI prediction section"""

        if not ai_prediction:
            return ""

        risk_color = "#dc3545" if ai_prediction["breakdown_probability"] >= 70 else "#ffc107" if ai_prediction["breakdown_probability"] >= 40 else "#28a745"

        return f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #17a2b8; margin: 15px 0;">
            <h4>🤖 AI Prediction Analysis</h4>
            <p><strong>Breakdown Probability:</strong>
                <span style="color: {risk_color}; font-weight: bold;">{ai_prediction["breakdown_probability"]}%</span>
            </p>
            <p><strong>Recommended Priority:</strong> {ai_prediction["recommended_priority"]}</p>

            {f'<p><strong>Additional Tasks:</strong> {", ".join(ai_prediction["additional_tasks"])}</p>' if ai_prediction.get("additional_tasks") else ''}

            {f'<p><strong>AI Notes:</strong> {ai_prediction["notes"]}</p>' if ai_prediction.get("notes") else ''}
        </div>
        """