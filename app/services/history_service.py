from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.models.objective import Objective
from app.models.cycle_review import CycleReview
from app.services.objective_service import ObjectiveService


class HistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_history_cycles(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Cycle).where(Cycle.user_id == user_id, Cycle.status == 1).order_by(Cycle.start_date.desc())
        )
        cycles = result.scalars().all()
        reviews_result = await self.db.execute(
            select(CycleReview).where(
                CycleReview.user_id == user_id,
                CycleReview.cycle_id.in_([cycle.id for cycle in cycles]),
            )
        ) if cycles else None
        reviews_by_cycle = {
            review.cycle_id: review.to_dict()
            for review in (reviews_result.scalars().all() if reviews_result else [])
        }
        output = []
        for c in cycles:
            obj_count = await self.db.execute(
                select(func.count(Objective.id)).where(Objective.cycle_id == c.id)
            )
            count = obj_count.scalar() or 0
            d = c.to_dict()
            d["objective_count"] = count
            d["review"] = reviews_by_cycle.get(c.id)
            output.append(d)
        return output

    async def get_history_objectives(self, user_id: int, cycle_id: int) -> Optional[list[dict]]:
        cycle = await self.db.get(Cycle, cycle_id)
        if not cycle or cycle.user_id != user_id:
            return None
        objective_service = ObjectiveService(self.db)
        return await objective_service.get_objectives(user_id, str(cycle_id), status=None)
