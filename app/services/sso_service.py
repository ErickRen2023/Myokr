from __future__ import annotations

import base64
import asyncio
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.utils.jwt_handler import create_access_token


class SsoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def ensure_configured() -> None:
        if not settings.SSO_CLIENT_ID or not settings.SSO_CLIENT_SECRET:
            raise ValueError("SSO is not configured")

    @staticmethod
    def create_authorization() -> tuple[str, str]:
        SsoService.ensure_configured()
        verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state = jwt.encode(
            {
                "nonce": nonce,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
                "type": "sso_state",
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        state_cookie = jwt.encode(
            {
                "nonce": nonce,
                "verifier": verifier,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
                "type": "sso_state_cookie",
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        query = urlencode({
            "response_type": "code",
            "client_id": settings.SSO_CLIENT_ID,
            "redirect_uri": settings.SSO_REDIRECT_URI,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "read:profile",
        })
        authorize_path = "/" + settings.SSO_AUTHORIZE_PATH.lstrip("/")
        return (
            f"{settings.SSO_PUBLIC_URL.rstrip('/')}{authorize_path}?{query}",
            state_cookie,
        )

    @staticmethod
    def decode_state(returned_state: str, state_cookie: str) -> str:
        try:
            state_payload = jwt.decode(
                returned_state,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            cookie_payload = jwt.decode(
                state_cookie,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError("SSO login state has expired") from exc
        if (
            state_payload.get("type") != "sso_state"
            or cookie_payload.get("type") != "sso_state_cookie"
            or not state_payload.get("nonce")
            or state_payload.get("nonce") != cookie_payload.get("nonce")
            or not cookie_payload.get("verifier")
        ):
            raise ValueError("Invalid SSO login state")
        return str(cookie_payload["verifier"])

    @staticmethod
    def encode_callback_result(result: dict) -> str:
        return jwt.encode(
            {
                **result,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=60),
                "type": "sso_callback_result",
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def decode_callback_result(token: str) -> dict:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.InvalidTokenError as exc:
            raise ValueError("SSO callback result has expired") from exc
        if payload.get("type") != "sso_callback_result":
            raise ValueError("Invalid SSO callback result")
        return {
            key: payload[key]
            for key in (
                "status", "token", "user_id", "username", "avatar"
            )
            if key in payload
        }

    @staticmethod
    async def fetch_userinfo(code: str, verifier: str) -> dict:
        SsoService.ensure_configured()
        token_body = await asyncio.to_thread(
            SsoService._request_json,
            f"{settings.SSO_SERVER_URL}/oauth/token",
            urlencode({
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.SSO_CLIENT_ID,
                "client_secret": settings.SSO_CLIENT_SECRET,
                "redirect_uri": settings.SSO_REDIRECT_URI,
                "code_verifier": verifier,
            }).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        access_token = token_body["access_token"]
        body = await asyncio.to_thread(
            SsoService._request_json,
            f"{settings.SSO_SERVER_URL}/oauth/userinfo",
            None,
            {"Authorization": f"Bearer {access_token}"},
        )
        return body.get("data", body)

    @staticmethod
    def _request_json(url: str, data: bytes | None, headers: dict[str, str]) -> dict:
        request = Request(url, data=data, headers=headers)
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    async def login_result(self, userinfo: dict) -> dict:
        subject = userinfo.get("sub")
        if subject is None:
            raise ValueError("SSO did not return a user subject")
        try:
            user_id = int(subject)
        except (TypeError, ValueError) as exc:
            raise ValueError("SSO returned an invalid user id") from exc
        if user_id <= 0 or str(user_id) != str(subject):
            raise ValueError("SSO returned an invalid user id")
        user = await self.db.get(User, user_id)
        profile = {
            key: value
            for key, value in {
                "username": userinfo.get("preferred_username"),
                "avatar": userinfo.get("avatar"),
            }.items()
            if value
        }
        if not user:
            user = User(id=user_id)
            self.db.add(user)
        await self.db.flush()
        return {
            "status": "authenticated",
            "token": create_access_token(user.id),
            "user_id": user.id,
            **profile,
        }
