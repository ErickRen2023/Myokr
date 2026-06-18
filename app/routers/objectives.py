from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.objective_service import ObjectiveService
from app.utils.response import success

router = APIRouter(prefix="/api/objectives", tags=["objectives"])


class CreateObjectiveRequest(BaseModel):
    cycle_id: int
    title: str
    description: Optional[str] = None
    sort_order: Optional[int] = None


class UpdateObjectiveRequest(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    cycle_id: Optional[int] = None
    sort_order: Optional[int] = None


class ObjectiveActionRequest(BaseModel):
    id: int


@router.get("")
async def list_objectives(cycle_id: str, status: Optional[int] = None, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ObjectiveService(db)
    objectives = await service.get_objectives(user_id, cycle_id, status)
    return success({"objectives": objectives})


@router.post("/create")
async def create_objective(req: CreateObjectiveRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ObjectiveService(db)
    obj = await service.create_objective(user_id, req.cycle_id, req.title, req.description, req.sort_order)
    return success(obj)


@router.post("/update")
async def update_objective(req: UpdateObjectiveRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ObjectiveService(db)
    obj = await service.update_objective(user_id, req.id, req.title, req.description, req.cycle_id, req.sort_order)
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")
    return success(obj)


@router.post("/archive")
async def archive_objective(req: ObjectiveActionRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ObjectiveService(db)
    await service.archive_objective(user_id, req.id)
    return success(None)


@router.post("/restore")
async def restore_objective(req: ObjectiveActionRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ObjectiveService(db)
    await service.restore_objective(user_id, req.id)
    return success(None)
