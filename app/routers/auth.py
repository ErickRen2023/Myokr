from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.sso_service import SsoService
from app.config import settings
from app.utils.response import success

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/sso/login")
async def sso_login():
    try:
        authorize_url, state_cookie = SsoService.create_authorization()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    response = RedirectResponse(authorize_url, status_code=302)
    response.set_cookie(
        "myokr_sso_state",
        state_cookie,
        max_age=600,
        httponly=True,
        secure=settings.SSO_COOKIE_SECURE,
        samesite="lax",
        path="/api/auth/sso/callback",
    )
    return response


@router.get("/sso/callback")
async def sso_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        params = urlencode({"error": error or "invalid_callback"})
        response = RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/sso/callback?{params}", status_code=302
        )
        response.delete_cookie("myokr_sso_state", path="/api/auth/sso/callback")
        return response
    try:
        verifier = SsoService.decode_state(
            state, request.cookies.get("myokr_sso_state", "")
        )
        userinfo = await SsoService.fetch_userinfo(code, verifier)
        result = await SsoService(db).login_result(userinfo)
        logger.info("aSSO callback completed with status=%s", result["status"])
    except Exception:
        logger.exception("aSSO callback failed")
        response = RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/sso/callback?error=sso_login_failed",
            status_code=302,
        )
        response.delete_cookie("myokr_sso_state", path="/api/auth/sso/callback")
        return response
    response = RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/sso/callback", status_code=302
    )
    response.set_cookie(
        "myokr_sso_result",
        SsoService.encode_callback_result(result),
        max_age=60,
        httponly=True,
        secure=settings.SSO_COOKIE_SECURE,
        samesite="lax",
        path="/api/auth/sso/result",
    )
    response.delete_cookie("myokr_sso_state", path="/api/auth/sso/callback")
    return response


@router.get("/sso/result")
async def sso_result(request: Request):
    result_cookie = request.cookies.get("myokr_sso_result", "")
    try:
        result = SsoService.decode_callback_result(result_cookie)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    response = JSONResponse(content=success(result))
    response.delete_cookie("myokr_sso_result", path="/api/auth/sso/result")
    return response
