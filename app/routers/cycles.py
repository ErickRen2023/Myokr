from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.cycle_service import CycleService
from app.utils.response import success

router = APIRouter(prefix="/api/cycles", tags=["cycles"])


class CreateCycleRequest(BaseModel):
    type: int
    start_date: str
    end_date: str


class UpdateCycleRequest(BaseModel):
    id: int
    end_date: Optional[str] = None
    start_date: Optional[str] = None
    type: Optional[int] = None


class CycleActionRequest(BaseModel):
    id: int


@router.get("")
async def list_cycles(status: Optional[int] = None, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = CycleService(db)
    cycles = await service.get_cycles(user_id, status)
    return success({"cycles": cycles})


@router.post("/create")
async def create_cycle(req: CreateCycleRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = CycleService(db)
    cycle = await service.create_cycle(user_id, req.type, req.start_date, req.end_date)
    return success(cycle)


@router.post("/update")
async def update_cycle(req: UpdateCycleRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = CycleService(db)
    cycle = await service.update_cycle(user_id, req.id, req.start_date, req.end_date, req.type)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return success(cycle)


@router.post("/archive")
async def archive_cycle(req: CycleActionRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = CycleService(db)
    await service.archive_cycle(user_id, req.id)
    return success(None)


@router.post("/reactivate")
async def reactivate_cycle(req: CycleActionRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = CycleService(db)
    await service.reactivate_cycle(user_id, req.id)
    return success(None)
