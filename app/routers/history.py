from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.history_service import HistoryService
from app.utils.response import success

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/cycles")
async def list_history_cycles(user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = HistoryService(db)
    cycles = await service.get_history_cycles(user_id)
    return success({"cycles": cycles})


@router.get("/objectives")
async def list_history_objectives(cycle_id: int, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = HistoryService(db)
    objectives = await service.get_history_objectives(user_id, cycle_id)
    if objectives is None:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return success({"objectives": objectives})
