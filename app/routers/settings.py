from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.utils.response import success

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ResetKeyRequest(BaseModel):
    secret_key: str


@router.post("/reset-key")
async def reset_key(req: ResetKeyRequest, user_id: int = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.reset_key(user_id, req.secret_key)
    if result is None:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    return success(result)
