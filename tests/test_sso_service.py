from urllib.parse import parse_qs, urlparse

import jwt
import pytest

from app.config import settings
from app.models.user import User
from app.services.sso_service import SsoService


class _Scalars:
    def __init__(self, value):
        self.value = value

    def first(self):
        return self.value


class _Result:
    def __init__(self, value):
        self.value = value

    def scalars(self):
        return _Scalars(self.value)


class _FakeDb:
    def __init__(self, results):
        self.results = list(results)
        self.added = []
        self.flushed = False

    async def execute(self, _statement):
        return _Result(self.results.pop(0))

    async def get(self, _model, _identifier):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushed = True


def test_authorization_uses_pkce_and_validates_state(monkeypatch):
    monkeypatch.setattr(settings, "SSO_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "SSO_CLIENT_SECRET", "client-secret")

    url, state_cookie = SsoService.create_authorization()
    query = parse_qs(urlparse(url).query)

    assert urlparse(url).path == "/authorize"
    assert query["client_id"] == ["client-id"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"][0]
    state_payload = jwt.decode(
        query["state"][0],
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert "verifier" not in state_payload
    assert SsoService.decode_state(query["state"][0], state_cookie)

    with pytest.raises(ValueError, match="SSO login state has expired"):
        SsoService.decode_state("wrong-state", state_cookie)

    _, other_cookie = SsoService.create_authorization()
    with pytest.raises(ValueError, match="Invalid SSO login state"):
        SsoService.decode_state(query["state"][0], other_cookie)


def test_callback_result_round_trip():
    encoded = SsoService.encode_callback_result({
        "status": "authenticated",
        "token": "local-token",
        "user_id": 42,
        "username": "alice",
        "avatar": "https://example.com/avatar.png",
    })
    assert SsoService.decode_callback_result(encoded) == {
        "status": "authenticated",
        "token": "local-token",
        "user_id": 42,
        "username": "alice",
        "avatar": "https://example.com/avatar.png",
    }


@pytest.mark.asyncio
async def test_new_sso_account_creates_okr_user():
    db = _FakeDb([None])
    result = await SsoService(db).login_result({
        "sub": "42",
        "preferred_username": "alice",
        "email": "alice@example.com",
        "avatar": "https://example.com/avatar.png",
    })

    assert result["status"] == "authenticated"
    assert result["user_id"] == 42
    payload = jwt.decode(
        result["token"],
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["sub"] == "42"
    assert db.flushed
    assert len(db.added) == 1
    user = db.added[0]
    assert user.id == 42


@pytest.mark.asyncio
async def test_existing_sso_account_logs_into_same_okr_user_without_copying_profile():
    user = User(
        id=42,
    )
    db = _FakeDb([user])
    result = await SsoService(db).login_result({
        "sub": "42",
        "preferred_username": "alice",
        "email": "alice@example.com",
        "avatar": "https://example.com/avatar.png",
    })

    assert result["status"] == "authenticated"
    assert result["user_id"] == 42
    assert result["username"] == "alice"
    assert result["avatar"] == "https://example.com/avatar.png"
    payload = jwt.decode(
        result["token"],
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload["sub"] == "42"
    assert db.flushed
    assert not db.added


@pytest.mark.asyncio
async def test_sso_account_rejects_non_numeric_user_id():
    with pytest.raises(ValueError, match="invalid user id"):
        await SsoService(_FakeDb([])).login_result({"sub": "sso-user-1"})
