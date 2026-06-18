from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.milestone_service import MilestoneService
from app.utils.response import success

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


class CreateMilestoneRequest(BaseModel):
    key_result_id: int
    description: str
    sort_order: Optional[int] = None


class UpdateMilestoneRequest(BaseModel):
    id: int
    description: Optional[str] = None


class ToggleMilestoneRequest(BaseModel):
    id: int


class DeleteMilestoneRequest(BaseModel):
    id: int


class ReorderMilestoneRequest(BaseModel):
    id: int
    sort_order: int


@router.get("")
async def list_milestones(key_result_id: int, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    milestones = await service.get_milestones(user_id, key_result_id)
    return success({"milestones": milestones})


@router.post("/create")
async def create_milestone(req: CreateMilestoneRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    milestone = await service.create_milestone(user_id, req.key_result_id, req.description, req.sort_order)
    if not milestone:
        raise HTTPException(status_code=404, detail="Key result not found")
    return success(milestone)


@router.post("/toggle")
async def toggle_milestone(req: ToggleMilestoneRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    milestone = await service.toggle_milestone(user_id, req.id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return success(milestone)


@router.post("/update")
async def update_milestone(req: UpdateMilestoneRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    milestone = await service.update_milestone(user_id, req.id, req.description)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return success(milestone)


@router.post("/reorder")
async def reorder_milestones(req: list[ReorderMilestoneRequest], user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    await service.reorder_milestones(user_id, [item.model_dump() for item in req])
    return success(None)


@router.post("/delete")
async def delete_milestone(req: DeleteMilestoneRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = MilestoneService(db)
    await service.delete_milestone(user_id, req.id)
    return success(None)
