from typing import Any, Optional

# Error codes aligned with tech spec 4.1.2
CODE_SUCCESS = 0
CODE_BAD_REQUEST = 40001
CODE_UNAUTHENTICATED = 40100
CODE_FORBIDDEN = 40300
CODE_NOT_FOUND = 40400
CODE_CONFLICT = 40900
CODE_INTERNAL_ERROR = 50000


def success(data: Any = None) -> dict:
    return {"code": CODE_SUCCESS, "message": "ok", "data": data}


def error(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}
