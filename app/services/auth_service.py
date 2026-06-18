import time
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cycle import Cycle
from app.models.user import User
from app.utils.key_generator import generate_secret_key
from app.utils.security import hash_key, hash_key_prefix, verify_key
from app.utils.jwt_handler import create_access_token


class AuthService:
    # Simple in-memory rate limiter: {identifier: [timestamps]}
    _rate_limit_store: dict[str, list[float]] = {}
    _RATE_LIMIT_WINDOW = 60  # seconds
    _RATE_LIMIT_MAX = 5

    @classmethod
    def _check_rate_limit(cls, identifier: str) -> bool:
        now = time.time()
        window_start = now - cls._RATE_LIMIT_WINDOW
        attempts = cls._rate_limit_store.get(identifier, [])
        attempts = [t for t in attempts if t > window_start]
        cls._rate_limit_store[identifier] = attempts
        if len(attempts) >= cls._RATE_LIMIT_MAX:
            return False
        attempts.append(now)
        return True

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_identity(self) -> dict:
        raw_key = generate_secret_key()
        hashed = hash_key(raw_key)
        prefix = hash_key_prefix(raw_key)
        user = User(key_hash=hashed, key_prefix=prefix)
        self.db.add(user)
        await self.db.flush()

        token = create_access_token(user.id)
        return {
            "secret_key": raw_key,
            "token": token,
            "user_id": user.id,
        }

    async def login(self, secret_key: str) -> Optional[dict]:
        prefix = hash_key_prefix(secret_key)
        result = await self.db.execute(
            select(User).where(User.key_prefix == prefix)
        )
        user = result.scalars().first()
        if user and verify_key(secret_key, user.key_hash):
            token = create_access_token(user.id)
            return {"token": token, "user_id": user.id}

        # Fallback: scan users with empty key_prefix (backward compat)
        result = await self.db.execute(
            select(User).where(User.key_prefix == "")
        )
        for user in result.scalars().all():
            if verify_key(secret_key, user.key_hash):
                user.key_prefix = prefix
                await self.db.flush()
                token = create_access_token(user.id)
                return {"token": token, "user_id": user.id}
        return None

    async def reset_key(self, user_id: int, current_secret_key: str) -> Optional[dict]:
        user = await self.db.get(User, user_id)
        if not user:
            return None
        if not verify_key(current_secret_key, user.key_hash):
            return None

        raw_key = generate_secret_key()
        user.key_hash = hash_key(raw_key)
        user.key_prefix = hash_key_prefix(raw_key)
        await self.db.flush()

        token = create_access_token(user.id)
        return {
            "new_secret_key": raw_key,
            "token": token,
        }

    async def get_user_info(self, user_id: int) -> Optional[dict]:
        user = await self.db.get(User, user_id)
        if not user:
            return None

        result = await self.db.execute(
            select(func.count(Cycle.id)).where(Cycle.user_id == user_id)
        )
        cycle_count = result.scalar() or 0

        return {
            "key_hash": user.key_hash,
            "create_time": user.create_time.isoformat() if user.create_time else None,
            "cycle_count": cycle_count,
        }
