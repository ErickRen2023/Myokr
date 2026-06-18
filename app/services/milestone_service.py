from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.key_result import KeyResult
from app.models.milestone import Milestone
from app.models.objective import Objective


class MilestoneService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_kr_ownership(self, user_id: int, kr_id: int) -> bool:
        kr = await self.db.get(KeyResult, kr_id)
        if not kr or kr.status != 0:
            return False
        obj = await self.db.get(Objective, kr.objective_id)
        return obj is not None and obj.user_id == user_id

    async def _check_milestone_ownership(self, user_id: int, ms_id: int) -> Optional[Milestone]:
        ms = await self.db.get(Milestone, ms_id)
        if not ms or ms.is_deleted != 0:
            return None
        kr = await self.db.get(KeyResult, ms.key_result_id)
        if not kr or kr.status != 0:
            return None
        obj = await self.db.get(Objective, kr.objective_id)
        if not obj or obj.user_id != user_id:
            return None
        return ms

    async def get_milestones(self, user_id: int, kr_id: int) -> list[dict]:
        if not await self._check_kr_ownership(user_id, kr_id):
            return []
        result = await self.db.execute(
            select(Milestone).where(
                Milestone.key_result_id == kr_id,
                Milestone.is_deleted == 0,
            ).order_by(Milestone.sort_order)
        )
        return [m.to_dict() for m in result.scalars().all()]

    async def create_milestone(self, user_id: int, kr_id: int, description: str, sort_order: Optional[int]) -> Optional[dict]:
        if not await self._check_kr_ownership(user_id, kr_id):
            return None
        if sort_order is None:
            result = await self.db.execute(
                select(Milestone).where(Milestone.key_result_id == kr_id, Milestone.is_deleted == 0)
            )
            sort_order = len(result.scalars().all())
        ms = Milestone(key_result_id=kr_id, description=description, sort_order=sort_order)
        self.db.add(ms)
        await self.db.flush()
        return ms.to_dict()

    async def toggle_milestone(self, user_id: int, ms_id: int) -> Optional[dict]:
        ms = await self._check_milestone_ownership(user_id, ms_id)
        if not ms:
            return None
        ms.completed = not ms.completed
        await self.db.flush()
        return ms.to_dict()

    async def update_milestone(self, user_id: int, ms_id: int, description: Optional[str]) -> Optional[dict]:
        ms = await self._check_milestone_ownership(user_id, ms_id)
        if not ms:
            return None
        if description is not None:
            ms.description = description
        await self.db.flush()
        return ms.to_dict()

    async def reorder_milestones(self, user_id: int, items: list[dict]) -> None:
        for item in items:
            ms = await self._check_milestone_ownership(user_id, item["id"])
            if ms:
                ms.sort_order = item["sort_order"]
        await self.db.flush()

    async def delete_milestone(self, user_id: int, ms_id: int) -> None:
        ms = await self._check_milestone_ownership(user_id, ms_id)
        if not ms:
            raise ValueError("Milestone not found")
        ms.is_deleted = 1
        await self.db.flush()
