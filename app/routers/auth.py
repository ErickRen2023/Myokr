from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.services.auth_service import AuthService
from app.utils.response import success

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    secret_key: str


@router.post("/generate-key")
async def generate_key(db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.generate_identity()
    return success(result)


@router.post("/login")
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    if not AuthService._check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts")
    service = AuthService(db)
    result = await service.login(req.secret_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid secret key")
    return success(result)
