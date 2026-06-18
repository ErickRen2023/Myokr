from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.dashboard_service import DashboardService
from app.utils.response import success

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard(cycle_id: str, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = DashboardService(db)
    result = await service.get_dashboard(user_id, cycle_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return success(result)
