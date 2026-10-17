"""Exercise upgrades from an existing database, never the configured MySQL."""

import asyncio
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Numeric, Table, event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import main
from app.config import settings
from app.database import get_db
from app.models.base import Base
from app.utils.jwt_handler import create_access_token


@pytest.mark.parametrize("legacy", [True, False], ids=["existing-database", "fresh-database"])
def test_startup_upgrades_schema_before_progress_requests(tmp_path, monkeypatch, legacy):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'okr.db'}", poolclass=NullPool)
    statements = []
    event.listen(engine.sync_engine, "before_cursor_execute", lambda conn, cursor, statement, parameters, context, many: statements.append(statement))
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name == "progress_record" and legacy:
            Table("progress_record", metadata,
                  Column("id", Integer, primary_key=True),
                  Column("key_result_id", Integer, nullable=False),
                  Column("value", Numeric(10, 2), nullable=False),
                  Column("is_achieved", Boolean, nullable=False),
                  Column("recorded_at", DateTime, nullable=False))
        else:
            copied = table.to_metadata(metadata)
            for column in copied.primary_key.columns:
                column.type = column.type.with_variant(Integer, "sqlite")

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)
            await connection.execute(metadata.tables["cycle"].insert().values(
                id=1, user_id=1, name="Local regression", type=3,
                start_date=date(2026, 10, 1), end_date=date(2026, 12, 31), status=0))
            await connection.execute(metadata.tables["objective"].insert().values(
                id=1, user_id=1, cycle_id=1, title="Local regression", sort_order=0, status=0))
            for identifier, kind, target, current in [
                (1, 1, {"value": 10, "unit": "天", "operator": "lte"}, None),
                (2, 1, {"value": 10, "unit": "天"}, 3),
                (3, 3, {}, None),
            ]:
                await connection.execute(metadata.tables["key_result"].insert().values(
                    id=identifier, objective_id=1, title=f"KR {identifier}", type=kind,
                    target=target, current_value=current, is_achieved=False, sort_order=identifier, status=0))
            await connection.execute(metadata.tables["progress_record"].insert().values(
                id=1, key_result_id=2, value=3, is_achieved=False, recorded_at=datetime(2026, 10, 15, 12)))
    asyncio.run(prepare())

    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(settings, "JWT_SECRET", "isolated-local-schema-upgrade-test-secret")
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def local_db():
        async with sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setitem(main.app.dependency_overrides, get_db, local_db)
    headers = {"Authorization": f"Bearer {create_access_token(1)}"}

    def request(client, method, path, **kwargs):
        response = client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 0, body
        return body["data"]

    with TestClient(main.app) as client:
        records = request(client, "GET", "/api/progress-records", params={"key_result_id": 2})["records"]
        assert len(records) == 1
        assert records[0] == {"id": 1, "value": 3.0, "is_achieved": False,
                              "target_snapshot": None, "recorded_at": "2026-10-15T12:00:00"}
        for value, achieved in [(0, True), (6, True), (10, True), (11, False), (6, True)]:
            updated = request(client, "POST", "/api/key-results/update-progress", json={"id": 1, "value": value})
            assert updated["current_value"] == value
            assert updated["is_achieved"] is achieved
            dashboard = request(client, "GET", "/api/dashboard", params={"cycle_id": 1})
            assert next(kr for kr in dashboard["objectives"][0]["key_results"] if kr["id"] == 1) == updated
        lower = request(client, "POST", "/api/key-results/update-progress", json={"id": 2, "value": 6})
        assert lower["current_value"] == 6 and lower["progress"] == 60
        boolean = request(client, "POST", "/api/key-results/toggle-achieved", json={"id": 3, "is_achieved": 1})
        assert boolean["is_achieved"]
        changed = request(client, "POST", "/api/key-results/update", json={"id": 1, "target": {"value": 5}})
        assert changed["target"]["operator"] == "lte" and not changed["is_achieved"]

    # A second process startup must keep both legacy data and new writes,
    # without repeating ALTER or requiring a separate deployment command.
    with TestClient(main.app) as client:
        dashboard = request(client, "GET", "/api/dashboard", params={"cycle_id": 1})
        upper = next(kr for kr in dashboard["objectives"][0]["key_results"] if kr["id"] == 1)
        assert upper["current_value"] == 6 and not upper["is_achieved"]
        records = request(client, "GET", "/api/progress-records", params={"key_result_id": 2})["records"]
        assert len(records) == 2
        assert records[-1]["id"] == 1 and records[-1]["target_snapshot"] is None
    assert sum(statement.startswith("ALTER TABLE") for statement in statements) == int(legacy)
