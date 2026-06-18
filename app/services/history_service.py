from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.models.objective import Objective
from app.services.objective_service import ObjectiveService


class HistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_history_cycles(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Cycle).where(Cycle.user_id == user_id, Cycle.status == 1).order_by(Cycle.start_date.desc())
        )
        cycles = result.scalars().all()
        output = []
        for c in cycles:
            obj_count = await self.db.execute(
                select(func.count(Objective.id)).where(Objective.cycle_id == c.id)
            )
            count = obj_count.scalar() or 0
            d = c.to_dict()
            d["objective_count"] = count
            output.append(d)
        return output

    async def get_history_objectives(self, user_id: int, cycle_id: int) -> Optional[list[dict]]:
        cycle = await self.db.get(Cycle, cycle_id)
        if not cycle or cycle.user_id != user_id:
            return None
        objective_service = ObjectiveService(self.db)
        return await objective_service.get_objectives(user_id, str(cycle_id), status=None)
