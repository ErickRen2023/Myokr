from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.progress_service import ProgressService
from app.utils.response import success

router = APIRouter(prefix="/api/progress-records", tags=["progress"])


@router.get("")
async def list_progress_records(key_result_id: int, limit: int = 50, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = ProgressService(db)
    records = await service.get_progress_records(user_id, key_result_id, limit)
    if records is None:
        raise HTTPException(status_code=404, detail="Key result not found")
    return success({"records": records})
