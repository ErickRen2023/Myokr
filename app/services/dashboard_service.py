from typing import Optional
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.services.objective_service import ObjectiveService


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self, user_id: int, cycle_id_str: str) -> Optional[dict]:
        cycle_ids = [int(x) for x in cycle_id_str.split(",") if x]
        first_cycle = await self.db.get(Cycle, cycle_ids[0])
        if not first_cycle or first_cycle.user_id != user_id:
            return None

        objective_service = ObjectiveService(self.db)
        objectives = await objective_service.get_objectives(user_id, cycle_id_str, status=0)

        all_krs = []
        for obj in objectives:
            for kr in obj["key_results"]:
                all_krs.append(kr)

        total_krs = len(all_krs)
        avg_progress = round(sum(kr["progress"] for kr in all_krs) / total_krs) if total_krs else 0.0

        today = date.today()
        cycles = []
        for cid in cycle_ids:
            c = await self.db.get(Cycle, cid)
            if c and c.user_id == user_id:
                remaining = max(0, (c.end_date - today).days)
                d = c.to_dict()
                d["remaining_days"] = remaining
                cycles.append(d)

        return {
            "cycles": cycles,
            "summary": {
                "total_objectives": len(objectives),
                "completed_objectives": sum(1 for o in objectives if o["progress"] >= 100),
                "in_progress_objectives": sum(1 for o in objectives if o["progress"] < 100),
                "total_key_results": total_krs,
                "average_kr_progress": avg_progress,
            },
            "objectives": objectives,
        }
