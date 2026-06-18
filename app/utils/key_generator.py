import secrets
import string

CHARSET = string.ascii_letters + string.digits  # base62


def generate_secret_key(length: int = 32) -> str:
    return "".join(secrets.choice(CHARSET) for _ in range(length))
