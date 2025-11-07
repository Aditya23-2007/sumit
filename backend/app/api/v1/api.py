from fastapi import APIRouter

from app.api.v1.endpoints import auth, equipment, maintenance, alerts, departments, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["equipment"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])