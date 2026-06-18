from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.key_result import KeyResult
from app.models.objective import Objective
from app.models.progress_record import ProgressRecord


class ProgressService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_progress_records(self, user_id: int, kr_id: int, limit: int = 50) -> Optional[list[dict]]:
        kr = await self.db.get(KeyResult, kr_id)
        if not kr:
            return None
        obj = await self.db.get(Objective, kr.objective_id)
        if not obj or obj.user_id != user_id:
            return None

        result = await self.db.execute(
            select(ProgressRecord)
            .where(ProgressRecord.key_result_id == kr_id)
            .order_by(ProgressRecord.recorded_at.desc())
            .limit(limit)
        )
        return [r.to_dict() for r in result.scalars().all()]
