from typing import Optional
from math import isfinite
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.key_result import KeyResult
from app.models.milestone import Milestone
from app.models.objective import Objective
from app.models.progress_record import ProgressRecord
from app.services.kr_evaluation import evaluate_kr, evaluate_numeric, validate_numeric_target


class KeyResultService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_objective_ownership(self, user_id: int, objective_id: int) -> bool:
        obj = await self.db.get(Objective, objective_id)
        return obj is not None and obj.user_id == user_id and obj.status == 0

    async def _check_kr_ownership(self, user_id: int, kr_id: int) -> Optional[KeyResult]:
        kr = await self.db.get(KeyResult, kr_id)
        if not kr or kr.status != 0:
            return None
        obj = await self.db.get(Objective, kr.objective_id)
        if not obj or obj.user_id != user_id:
            return None
        return kr

    async def get_key_results(self, user_id: int, objective_id_str: str) -> list[dict]:
        obj_ids = [int(x) for x in objective_id_str.split(",") if x]
        result = await self.db.execute(
            select(KeyResult).where(KeyResult.objective_id.in_(obj_ids), KeyResult.status == 0).order_by(KeyResult.sort_order, KeyResult.id)
        )
        krs = result.scalars().all()
        authorized = []
        for kr in krs:
            obj = await self.db.get(Objective, kr.objective_id)
            if obj and obj.user_id == user_id:
                authorized.append(kr)
        return [await self._serialize_kr(kr) for kr in authorized]

    async def _serialize_kr(self, kr: KeyResult) -> dict:
        milestones = []
        ms_list = []
        if kr.type == 2:
            ms_result = await self.db.execute(
                select(Milestone).where(
                    Milestone.key_result_id == kr.id,
                    Milestone.is_deleted == 0,
                ).order_by(Milestone.sort_order)
            )
            ms_list = ms_result.scalars().all()
            milestones = [m.to_dict() for m in ms_list]
        d = kr.to_dict()
        d.update(evaluate_kr(kr, ms_list))
        d["milestones"] = milestones
        return d

    def _compute_progress(self, kr: KeyResult) -> float:
        return evaluate_kr(kr)["progress"]

    async def create_key_result(self, user_id: int, objective_id: int, title: str, description: Optional[str], kr_type: int, target: Optional[dict], milestones_input: Optional[list[dict]], sort_order: Optional[int] = None) -> Optional[dict]:
        if not await self._check_objective_ownership(user_id, objective_id):
            return None
        if kr_type == 1:
            target = validate_numeric_target(target or {})
        if sort_order is None:
            result = await self.db.execute(
                select(KeyResult).where(KeyResult.objective_id == objective_id, KeyResult.status == 0)
            )
            sort_order = len(result.scalars().all())
        kr = KeyResult(
            objective_id=objective_id, title=title, description=description, type=kr_type,
            target=target or {}, sort_order=sort_order, status=0,
        )
        self.db.add(kr)
        await self.db.flush()
        if kr_type == 2 and milestones_input:
            for i, m in enumerate(milestones_input):
                ms = Milestone(
                    key_result_id=kr.id, description=m["description"],
                    sort_order=m.get("sort_order", i),
                )
                self.db.add(ms)
            await self.db.flush()
        return await self._serialize_kr(kr)

    async def update_key_result(self, user_id: int, kr_id: int, title: Optional[str], description: Optional[str], target: Optional[dict], sort_order: Optional[int] = None) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
        if title is not None:
            kr.title = title
        if description is not None:
            kr.description = description
        if target is not None:
            if kr.type == 1:
                next_target = validate_numeric_target({**(kr.target or {}), **target})
                changed = next_target != {"operator": "gte", **(kr.target or {})}
                kr.target = next_target
                kr.is_achieved = evaluate_numeric(next_target, kr.current_value)["is_achieved"]
                if changed and kr.current_value is not None:
                    self.db.add(ProgressRecord(
                        key_result_id=kr.id, value=kr.current_value,
                        is_achieved=kr.is_achieved, target_snapshot=dict(next_target),
                    ))
            else:
                kr.target = target
        if sort_order is not None:
            kr.sort_order = sort_order
        await self.db.flush()
        return await self._serialize_kr(kr)

    async def reorder_key_results(self, user_id: int, items: list[dict]) -> None:
        for item in items:
            kr = await self._check_kr_ownership(user_id, item["id"])
            if kr:
                kr.sort_order = item["sort_order"]
        await self.db.flush()

    async def update_progress(self, user_id: int, kr_id: int, value: float, is_achieved: Optional[bool] = None) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
        if kr.type != 1:
            raise ValueError("Progress update is only supported for numeric key results")
        if not isfinite(value) or value < 0:
            raise ValueError("当前值必须为非负有限数值")
        target = validate_numeric_target(kr.target or {})
        is_achieved_val = evaluate_numeric(target, value)["is_achieved"]
        kr.current_value = value
        kr.is_achieved = is_achieved_val
        record = ProgressRecord(key_result_id=kr_id, value=value, is_achieved=is_achieved_val, target_snapshot=dict(target))
        self.db.add(record)
        await self.db.flush()
        return await self._serialize_kr(kr)

    async def toggle_achieved(self, user_id: int, kr_id: int, achieved: bool) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
        if kr.type != 3:
            raise ValueError("只有布尔型关键结果可以手动标记达成")
        kr.is_achieved = achieved
        value = 100.0 if achieved else 0.0
        record = ProgressRecord(key_result_id=kr_id, value=value, is_achieved=achieved)
        self.db.add(record)
        await self.db.flush()
        return await self._serialize_kr(kr)

    async def archive_key_result(self, user_id: int, kr_id: int) -> None:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            raise ValueError("Key result not found")
        kr.status = 1
        await self.db.flush()
