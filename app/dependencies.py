from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.jwt_handler import decode_access_token


async def get_current_user(
    authorization: str = Header(...),
) -> int:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    try:
        user_id = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return user_id
