from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.cycle import Cycle
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


class CycleReviewRequest(BaseModel):
    cycle_id: int
    summary: str = Field(default="", max_length=5000)
    highlights: str = Field(default="", max_length=5000)
    blockers: str = Field(default="", max_length=5000)
    learnings: str = Field(default="", max_length=5000)
    next_steps: str = Field(default="", max_length=5000)

    def to_review_data(self) -> dict:
        return {
            "summary": self.summary.strip(),
            "highlights": self.highlights.strip(),
            "blockers": self.blockers.strip(),
            "learnings": self.learnings.strip(),
            "next_steps": self.next_steps.strip(),
        }


def validate_review_content(review_data: dict) -> None:
    if not any(review_data.values()):
        raise HTTPException(status_code=422, detail="请至少填写一项复盘内容")


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


@router.get("/{cycle_id}/review")
async def get_cycle_review(cycle_id: int, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cycle = await db.get(Cycle, cycle_id)
    if not cycle or cycle.user_id != user_id:
        raise HTTPException(status_code=404, detail="Cycle not found")
    service = CycleService(db)
    review = await service.get_cycle_review(user_id, cycle_id)
    return success({"review": review})


@router.post("/review")
async def save_cycle_review(req: CycleReviewRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    review_data = req.to_review_data()
    validate_review_content(review_data)
    service = CycleService(db)
    review = await service.save_cycle_review(user_id, req.cycle_id, review_data)
    if review is None:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return success({"review": review})


@router.post("/review-and-archive")
async def review_and_archive_cycle(req: CycleReviewRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    review_data = req.to_review_data()
    validate_review_content(review_data)
    service = CycleService(db)
    review = await service.review_and_archive_cycle(user_id, req.cycle_id, review_data)
    if review is None:
        raise HTTPException(status_code=404, detail="Cycle not found")
    return success({"review": review, "archived": True})
