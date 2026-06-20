import calendar
from typing import Optional
from datetime import date

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.models.key_result import KeyResult
from app.models.objective import Objective


class CycleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_name(self, cycle_type: int, start_date: date) -> str:
        year = start_date.year
        month = start_date.month
        if cycle_type == 1:
            return f"{year}年{month}月"
        elif cycle_type == 2:
            end_month = month + 1
            end_year = year
            if end_month > 12:
                end_month = 1
                end_year = year + 1
            if end_year != year:
                return f"{year}年{month}月-{end_year}年{end_month}月"
            return f"{year}年{month}月-{end_month}月"
        elif cycle_type == 3:
            quarter = (month - 1) // 3 + 1
            return f"{year}年Q{quarter}"
        elif cycle_type == 4:
            half = "上半年" if month <= 6 else "下半年"
            return f"{year}年{half}"
        elif cycle_type == 5:
            return f"{year}年"
        return ""

    @staticmethod
    def _validate_cycle_boundaries(cycle_type: int, start_date: date, end_date: date) -> None:
        if start_date.day != 1:
            raise ValueError("周期开始日期必须是该月的第一天")

        if cycle_type == 1:  # Monthly
            _, last_day = calendar.monthrange(start_date.year, start_date.month)
            expected_end = date(start_date.year, start_date.month, last_day)
            if end_date != expected_end:
                raise ValueError(f"月度周期的结束日期必须与该月最后一天一致 (应为 {expected_end})")

        elif cycle_type == 2:  # Bimonthly
            end_month = start_date.month + 1
            end_year = start_date.year
            if end_month > 12:
                end_month = 1
                end_year += 1
            _, last_day = calendar.monthrange(end_year, end_month)
            expected_end = date(end_year, end_month, last_day)
            if end_date != expected_end:
                raise ValueError(f"双月度周期的结束日期必须为第二个月的最后一天 (应为 {expected_end})")

        elif cycle_type == 3:  # Quarterly
            if start_date.month not in (1, 4, 7, 10):
                raise ValueError("季度周期的开始日期必须是 1 月、4 月、7 月或 10 月的第一天")
            q_end_month = {1: 3, 4: 6, 7: 9, 10: 12}[start_date.month]
            _, last_day = calendar.monthrange(start_date.year, q_end_month)
            expected_end = date(start_date.year, q_end_month, last_day)
            if end_date != expected_end:
                raise ValueError(f"季度周期的结束日期必须为该季度的最后一天 (应为 {expected_end})")

        elif cycle_type == 4:  # Half-year
            if start_date.month not in (1, 7):
                raise ValueError("半年度周期的开始日期必须是 1 月或 7 月的第一天")
            end_month = 6 if start_date.month == 1 else 12
            _, last_day = calendar.monthrange(start_date.year, end_month)
            expected_end = date(start_date.year, end_month, last_day)
            if end_date != expected_end:
                raise ValueError(f"半年度周期的结束日期必须为该半年的最后一天 (应为 {expected_end})")

        elif cycle_type == 5:  # Yearly
            if start_date.month != 1:
                raise ValueError("年度周期的开始日期必须是 1 月 1 日")
            expected_end = date(start_date.year, 12, 31)
            if end_date != expected_end:
                raise ValueError(f"年度周期的结束日期必须是 12 月 31 日 (应为 {expected_end})")

        else:
            raise ValueError(f"无效的周期类型: {cycle_type}")

    async def get_cycles(self, user_id: int, status: Optional[int] = 0) -> list[dict]:
        conditions = [Cycle.user_id == user_id]
        if status is not None:
            conditions.append(Cycle.status == status)
        result = await self.db.execute(
            select(Cycle).where(and_(*conditions)).order_by(Cycle.start_date.desc())
        )
        cycles = result.scalars().all()
        output = []
        for c in cycles:
            obj_count = await self.db.execute(
                select(func.count(Objective.id)).where(Objective.cycle_id == c.id, Objective.status == 0)
            )
            count = obj_count.scalar() or 0
            d = c.to_dict()
            d["objective_count"] = count
            output.append(d)
        return output

    async def create_cycle(self, user_id: int, cycle_type: int, start_date_str: str, end_date_str: str) -> dict:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        self._validate_cycle_boundaries(cycle_type, start_date, end_date)
        name = self._generate_name(cycle_type, start_date)
        cycle = Cycle(user_id=user_id, name=name, type=cycle_type, start_date=start_date, end_date=end_date)
        self.db.add(cycle)
        await self.db.flush()
        return cycle.to_dict()

    async def update_cycle(self, user_id: int, cycle_id: int, start_date_str: Optional[str], end_date_str: Optional[str], cycle_type: Optional[int]) -> Optional[dict]:
        cycle = await self.db.get(Cycle, cycle_id)
        if not cycle or cycle.user_id != user_id or cycle.status != 0:
            return None
        if start_date_str:
            cycle.start_date = date.fromisoformat(start_date_str)
        if end_date_str:
            cycle.end_date = date.fromisoformat(end_date_str)
        if cycle_type:
            cycle.type = cycle_type
        self._validate_cycle_boundaries(cycle.type, cycle.start_date, cycle.end_date)
        cycle.name = self._generate_name(cycle.type, cycle.start_date)
        await self.db.flush()
        return cycle.to_dict()

    async def archive_cycle(self, user_id: int, cycle_id: int) -> None:
        cycle = await self.db.get(Cycle, cycle_id)
        if not cycle or cycle.user_id != user_id:
            raise ValueError("Cycle not found")
        cycle.status = 1
        # 级联归档：该周期下所有活跃 O → 活跃 KR
        obj_result = await self.db.execute(
            select(Objective).where(Objective.cycle_id == cycle_id, Objective.status == 0)
        )
        for obj in obj_result.scalars().all():
            obj.status = 1
            kr_result = await self.db.execute(
                select(KeyResult).where(KeyResult.objective_id == obj.id, KeyResult.status == 0)
            )
            for kr in kr_result.scalars().all():
                kr.status = 1
        await self.db.flush()

    async def reactivate_cycle(self, user_id: int, cycle_id: int) -> None:
        cycle = await self.db.get(Cycle, cycle_id)
        if not cycle or cycle.user_id != user_id:
            raise ValueError("Cycle not found")
        cycle.status = 0
        # 级联恢复：该周期下所有已归档 O → 已归档 KR
        obj_result = await self.db.execute(
            select(Objective).where(Objective.cycle_id == cycle_id, Objective.status == 1)
        )
        for obj in obj_result.scalars().all():
            obj.status = 0
            kr_result = await self.db.execute(
                select(KeyResult).where(KeyResult.objective_id == obj.id, KeyResult.status == 1)
            )
            for kr in kr_result.scalars().all():
                kr.status = 0
        await self.db.flush()
