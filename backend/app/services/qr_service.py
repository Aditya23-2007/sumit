import qrcode
import io
import base64
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class QRCodeService:
    def __init__(self):
        self.base_url = settings.NEXT_PUBLIC_API_URL or "http://localhost:3000"

    async def generate_equipment_qr_code(
        self,
        equipment_id: str,
        equipment_name: str
    ) -> str:
        """Generate QR code for equipment linking to equipment details page"""

        try:
            # Create the URL that the QR code will point to
            equipment_url = f"{self.base_url}/equipment/{equipment_id}"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(equipment_url)
            qr.make(fit=True)

            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")

            # Add equipment name as a label (simplified - in production, you might want to use PIL to add text)
            # For now, we'll just return the QR code

            # Convert image to base64 string for easy frontend consumption
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            # Return as data URL
            qr_code_url = f"data:image/png;base64,{img_str}"

            logger.info(f"Generated QR code for equipment: {equipment_name}")
            return qr_code_url

        except Exception as e:
            logger.error(f"Failed to generate QR code for equipment {equipment_id}: {str(e)}")
            raise Exception(f"QR code generation failed: {str(e)}")

    async def generate_maintenance_qr_code(
        self,
        maintenance_log_id: str,
        equipment_name: str
    ) -> str:
        """Generate QR code for maintenance log linking to maintenance details"""

        try:
            # Create the URL that the QR code will point to
            maintenance_url = f"{self.base_url}/maintenance/{maintenance_log_id}"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(maintenance_url)
            qr.make(fit=True)

            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert image to base64 string
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            # Return as data URL
            qr_code_url = f"data:image/png;base64,{img_str}"

            logger.info(f"Generated QR code for maintenance log of equipment: {equipment_name}")
            return qr_code_url

        except Exception as e:
            logger.error(f"Failed to generate maintenance QR code: {str(e)}")
            raise Exception(f"QR code generation failed: {str(e)}")

    def generate_qr_code_file(self, data: str, filename: Optional[str] = None) -> bytes:
        """Generate QR code and return as bytes (for file generation)"""

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Failed to generate QR code file: {str(e)}")
            raise Exception(f"QR code generation failed: {str(e)}")

    async def batch_generate_equipment_qr_codes(
        self,
        equipment_list: list
    ) -> dict:
        """Generate QR codes for multiple equipment items"""

        results = {}
        errors = {}

        for equipment in equipment_list:
            try:
                equipment_id = equipment.get("id")
                equipment_name = equipment.get("name", "Unknown Equipment")

                if equipment_id:
                    qr_code_url = await self.generate_equipment_qr_code(
                        equipment_id=equipment_id,
                        equipment_name=equipment_name
                    )
                    results[equipment_id] = {
                        "equipment_name": equipment_name,
                        "qr_code_url": qr_code_url,
                        "status": "success"
                    }
                else:
                    errors[equipment_name] = "Missing equipment ID"

            except Exception as e:
                equipment_name = equipment.get("name", "Unknown Equipment")
                errors[equipment_name] = str(e)
                logger.error(f"Failed to generate QR code for {equipment_name}: {str(e)}")

        return {
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors
        }