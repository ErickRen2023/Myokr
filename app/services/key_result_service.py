from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.key_result import KeyResult
from app.models.milestone import Milestone
from app.models.objective import Objective
from app.models.progress_record import ProgressRecord


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
            select(KeyResult).where(KeyResult.objective_id.in_(obj_ids), KeyResult.status == 0)
        )
        krs = result.scalars().all()
        authorized = []
        for kr in krs:
            obj = await self.db.get(Objective, kr.objective_id)
            if obj and obj.user_id == user_id:
                authorized.append(kr)
        return [await self._serialize_kr(kr) for kr in authorized]

    async def _serialize_kr(self, kr: KeyResult) -> dict:
        progress = self._compute_progress(kr)
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
            done = sum(1 for m in ms_list if m.completed)
            progress = round(done / len(ms_list) * 100) if ms_list else 0
        d = kr.to_dict()
        d["progress"] = progress
        d["milestones"] = milestones
        return d

    def _compute_progress(self, kr: KeyResult) -> float:
        if kr.type == 3:
            return 100.0 if kr.is_achieved else 0.0
        if kr.type == 1 and kr.current_value is not None:
            target_val = kr.target.get("value", 1) if kr.target else 1
            if target_val == 0:
                target_val = 1
            return round(min(kr.current_value / target_val * 100, 100), 1)
        return 0.0

    async def create_key_result(self, user_id: int, objective_id: int, title: str, description: Optional[str], kr_type: int, target: Optional[dict], milestones_input: Optional[list[dict]]) -> Optional[dict]:
        if not await self._check_objective_ownership(user_id, objective_id):
            return None
        if kr_type == 1:
            if not target or not target.get("value") or not target.get("unit", "").strip():
                raise ValueError("目标值与单位不能为空")
            if not isinstance(target.get("value"), (int, float)) or target["value"] <= 0:
                raise ValueError("目标值必须为正数")
        kr = KeyResult(
            objective_id=objective_id, title=title, description=description, type=kr_type,
            target=target or {}, status=0,
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

    async def update_key_result(self, user_id: int, kr_id: int, title: Optional[str], description: Optional[str], target: Optional[dict]) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
        if title is not None:
            kr.title = title
        if description is not None:
            kr.description = description
        if target is not None:
            kr.target = target
        await self.db.flush()
        return await self._serialize_kr(kr)

    async def update_progress(self, user_id: int, kr_id: int, value: float, is_achieved: Optional[bool] = None) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
        if kr.type in (2, 3):
            raise ValueError("Progress update is only supported for numeric key results")
        is_achieved_val = is_achieved if is_achieved is not None else False
        if kr.type == 1:
            target_val = kr.target.get("value", 0) if kr.target else 0
            if target_val > 0 and value >= target_val:
                is_achieved_val = True
        kr.current_value = value
        kr.is_achieved = is_achieved_val
        record = ProgressRecord(key_result_id=kr_id, value=value, is_achieved=is_achieved_val)
        self.db.add(record)
        await self.db.flush()
        return await self._serialize_kr(kr)

    async def toggle_achieved(self, user_id: int, kr_id: int, achieved: bool) -> Optional[dict]:
        kr = await self._check_kr_ownership(user_id, kr_id)
        if not kr:
            return None
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
