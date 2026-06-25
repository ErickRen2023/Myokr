from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.key_result_service import KeyResultService
from app.utils.response import success

router = APIRouter(prefix="/api/key-results", tags=["key_results"])


class CreateKRRequest(BaseModel):
    objective_id: int
    title: str
    description: Optional[str] = None
    type: int
    target: Optional[dict] = None
    milestones: Optional[List[dict]] = None
    sort_order: Optional[int] = None


class UpdateKRRequest(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    target: Optional[dict] = None
    sort_order: Optional[int] = None


class UpdateProgressRequest(BaseModel):
    id: int
    value: float
    is_achieved: Optional[bool] = None


class ToggleAchievedRequest(BaseModel):
    id: int
    is_achieved: int


class KRActionRequest(BaseModel):
    id: int


class ReorderKRRequest(BaseModel):
    id: int
    sort_order: int


@router.get("")
async def list_key_results(objective_id: str, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    krs = await service.get_key_results(user_id, objective_id)
    return success({"key_results": krs})


@router.post("/create")
async def create_key_result(req: CreateKRRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    kr = await service.create_key_result(user_id, req.objective_id, req.title, req.description, req.type, req.target, req.milestones, req.sort_order)
    if not kr:
        raise HTTPException(status_code=404, detail="Objective not found")
    return success(kr)


@router.post("/update")
async def update_key_result(req: UpdateKRRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    kr = await service.update_key_result(user_id, req.id, req.title, req.description, req.target, req.sort_order)
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    return success(kr)


@router.post("/update-progress")
async def update_progress(req: UpdateProgressRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    kr = await service.update_progress(user_id, req.id, req.value, req.is_achieved)
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    return success(kr)


@router.post("/toggle-achieved")
async def toggle_achieved(req: ToggleAchievedRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    kr = await service.toggle_achieved(user_id, req.id, bool(req.is_achieved))
    if not kr:
        raise HTTPException(status_code=404, detail="Key result not found")
    return success(kr)


@router.post("/reorder")
async def reorder_key_results(req: list[ReorderKRRequest], user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    await service.reorder_key_results(user_id, [item.model_dump() for item in req])
    return success(None)


@router.post("/archive")
async def archive_key_result(req: KRActionRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = KeyResultService(db)
    await service.archive_key_result(user_id, req.id)
    return success(None)
