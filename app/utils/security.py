import hashlib

import bcrypt
from app.config import settings


def hash_key(raw_key: str) -> str:
    return bcrypt.hashpw(
        raw_key.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
    ).decode("utf-8")


def hash_key_prefix(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def verify_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), hashed.encode("utf-8"))
