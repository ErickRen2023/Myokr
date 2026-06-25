from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.models.key_result import KeyResult
from app.models.milestone import Milestone
from app.models.objective import Objective


def _kr_progress(kr: KeyResult, milestones: Optional[list[Milestone]] = None) -> float:
    if kr.type == 3:
        return 100.0 if kr.is_achieved else 0.0
    if kr.type == 2:
        if milestones is None:
            return 0.0
        done = sum(1 for m in milestones if m.completed)
        return round(done / len(milestones) * 100) if milestones else 0
    if kr.type == 1 and kr.current_value is not None:
        target_val = kr.target.get("value", 1) if kr.target else 1
        if target_val == 0:
            target_val = 1
        return round(min(kr.current_value / target_val * 100, 100), 1)
    return 0.0


class ObjectiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_cycle_ownership(self, user_id: int, cycle_id: int) -> bool:
        cycle = await self.db.get(Cycle, cycle_id)
        return cycle is not None and cycle.user_id == user_id and cycle.status == 0

    async def get_objectives(self, user_id: int, cycle_id_str: str, status: Optional[int] = None) -> list[dict]:
        cycle_ids = [int(x) for x in cycle_id_str.split(",") if x]
        conditions = [Objective.user_id == user_id, Objective.cycle_id.in_(cycle_ids)]
        if status is not None:
            conditions.append(Objective.status == status)
        result = await self.db.execute(
            select(Objective).where(and_(*conditions)).order_by(Objective.sort_order, Objective.id)
        )
        objectives = result.scalars().all()
        return [await self._serialize_objective(o) for o in objectives]

    async def _serialize_objective(self, o: Objective) -> dict:
        kr_result = await self.db.execute(
            select(KeyResult).where(KeyResult.objective_id == o.id, KeyResult.status == 0).order_by(KeyResult.sort_order, KeyResult.id)
        )
        krs = kr_result.scalars().all()
        kr_list = []
        total_progress = 0
        for kr in krs:
            kr_dict = await self._serialize_kr(kr)
            kr_list.append(kr_dict)
            total_progress += kr_dict["progress"]
        avg_progress = round(total_progress / len(krs)) if krs else 0
        d = o.to_dict()
        d["progress"] = avg_progress
        d["key_results"] = kr_list
        return d

    async def _serialize_kr(self, kr: KeyResult) -> dict:
        milestones = []
        if kr.type == 2:
            ms_result = await self.db.execute(
                select(Milestone).where(
                    Milestone.key_result_id == kr.id,
                    Milestone.is_deleted == 0,
                ).order_by(Milestone.sort_order)
            )
            ms_list = ms_result.scalars().all()
            milestones = [m.to_dict() for m in ms_list]
        progress = _kr_progress(kr, ms_list if kr.type == 2 else None)
        d = kr.to_dict()
        d["progress"] = progress
        d["milestones"] = milestones
        return d

    async def create_objective(self, user_id: int, cycle_id: int, title: str, description: Optional[str], sort_order: Optional[int]) -> Optional[dict]:
        if not await self._check_cycle_ownership(user_id, cycle_id):
            return None
        if sort_order is None:
            result = await self.db.execute(
                select(Objective).where(Objective.cycle_id == cycle_id)
            )
            existing = result.scalars().all()
            sort_order = len(existing)
        obj = Objective(user_id=user_id, cycle_id=cycle_id, title=title, description=description, sort_order=sort_order)
        self.db.add(obj)
        await self.db.flush()
        return await self._serialize_objective(obj)

    async def update_objective(self, user_id: int, obj_id: int, title: Optional[str], description: Optional[str], cycle_id: Optional[int], sort_order: Optional[int]) -> Optional[dict]:
        obj = await self.db.get(Objective, obj_id)
        if not obj or obj.user_id != user_id or obj.status != 0:
            return None
        if title is not None:
            obj.title = title
        if description is not None:
            obj.description = description
        if cycle_id is not None and await self._check_cycle_ownership(user_id, cycle_id):
            obj.cycle_id = cycle_id
        if sort_order is not None:
            obj.sort_order = sort_order
        await self.db.flush()
        return await self._serialize_objective(obj)

    async def archive_objective(self, user_id: int, obj_id: int) -> None:
        obj = await self.db.get(Objective, obj_id)
        if not obj or obj.user_id != user_id:
            raise ValueError("Objective not found")
        obj.status = 1
        # 级联归档：该 O 下所有活跃 KR
        kr_result = await self.db.execute(
            select(KeyResult).where(KeyResult.objective_id == obj_id, KeyResult.status == 0)
        )
        for kr in kr_result.scalars().all():
            kr.status = 1
        await self.db.flush()

    async def restore_objective(self, user_id: int, obj_id: int) -> None:
        obj = await self.db.get(Objective, obj_id)
        if not obj or obj.user_id != user_id:
            raise ValueError("Objective not found")
        obj.status = 0
        # 级联恢复：该 O 下所有已归档 KR
        kr_result = await self.db.execute(
            select(KeyResult).where(KeyResult.objective_id == obj_id, KeyResult.status == 1)
        )
        for kr in kr_result.scalars().all():
            kr.status = 0
        await self.db.flush()

    async def reorder_objectives(self, user_id: int, items: list[dict]) -> None:
        for item in items:
            obj = await self.db.get(Objective, item["id"])
            if obj and obj.user_id == user_id and obj.status == 0:
                obj.sort_order = item["sort_order"]
        await self.db.flush()
