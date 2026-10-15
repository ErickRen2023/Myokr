from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.key_result import KeyResult
from app.models.objective import Objective
from app.models.progress_record import ProgressRecord
from app.services.key_result_service import KeyResultService
from app.services.kr_evaluation import evaluate_numeric, validate_numeric_target
from app.services.objective_service import ObjectiveService


@pytest.mark.parametrize("current,achieved,progress", [(None, False, 0), (0, True, 100), (6, True, 100), (10, True, 100), (11, False, 0)])
def test_upper_bound(current, achieved, progress):
    result = evaluate_numeric({"value": 10, "unit": "天", "operator": "lte"}, current)
    assert result["is_achieved"] is achieved
    assert result["progress"] == progress
    assert result["usage_percent"] == (None if current is None else current * 10)


@pytest.mark.parametrize("current,achieved,progress", [(None, False, 0), (0, False, 0), (6, False, 60), (10, True, 100), (11, True, 100)])
def test_legacy_numeric_keeps_original_semantics(current, achieved, progress):
    result = evaluate_numeric({"value": 10, "unit": "天"}, current)
    assert result["is_achieved"] is achieved
    assert result["progress"] == progress


def test_zero_limit_and_rounding_do_not_define_achievement():
    assert evaluate_numeric({"value": 0, "operator": "lte"}, 0)["is_achieved"]
    assert not evaluate_numeric({"value": 0, "operator": "lte"}, 1)["is_achieved"]
    assert not evaluate_numeric({"value": 10}, 9.999)["is_achieved"]


@pytest.mark.parametrize("target", [
    {"value": 0, "unit": "天"}, {"value": -1, "unit": "天", "operator": "lte"},
    {"value": 10, "unit": "天", "operator": "lt"}, {"value": True, "unit": "天"},
    {"value": "10", "unit": "天"}, {"value": float("nan"), "unit": "天"},
    {"value": float("inf"), "unit": "天"}, {"value": 10, "unit": " "}, {"value": 10, "unit": None},
])
def test_invalid_targets(target):
    with pytest.raises(ValueError):
        validate_numeric_target(target)


def test_valid_zero_limit_and_default_operator():
    assert validate_numeric_target({"value": 0, "unit": "天", "operator": "lte"})["value"] == 0
    assert validate_numeric_target({"value": 10, "unit": "天"})["operator"] == "gte"


@pytest.fixture
def numeric_service():
    kr = KeyResult(id=1, objective_id=2, title="晚睡天数", type=1, target={"value": 10, "unit": "天", "operator": "lte"}, current_value=None, status=0, is_achieved=False)
    objective = Objective(id=2, user_id=3, status=0)
    db = MagicMock()
    db.get = AsyncMock(side_effect=lambda model, identifier: kr if model is KeyResult else objective)
    db.flush = AsyncMock()
    return KeyResultService(db), kr, db


@pytest.mark.asyncio
async def test_updates_cross_threshold_both_ways_and_keep_snapshots(numeric_service):
    service, kr, db = numeric_service
    for value, achieved in [(0, True), (10, True), (11, False), (6, True)]:
        result = await service.update_progress(3, 1, value, not achieved)
        assert result["is_achieved"] is achieved
        assert result == await ObjectiveService(db)._serialize_kr(kr)
    records = [call.args[0] for call in db.add.call_args_list]
    assert [record.is_achieved for record in records] == [True, True, False, True]
    await service.update_key_result(3, 1, None, None, {"value": 5, "unit": "天"})
    assert kr.target["operator"] == "lte"
    assert not kr.is_achieved
    assert records[-1].target_snapshot["value"] == 10
    assert records[-1].is_achieved
    assert db.add.call_args.args[0].target_snapshot["value"] == 5
    await service.update_key_result(3, 1, None, None, {"operator": "gte"})
    assert kr.is_achieved
    assert records[-1].target_snapshot["operator"] == "lte"


@pytest.mark.asyncio
async def test_unrecorded_remains_unknown_after_rule_change(numeric_service):
    service, kr, db = numeric_service
    result = await service.update_key_result(3, 1, None, None, {"value": 0})
    assert result["current_value"] is None
    assert not result["is_achieved"]
    db.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
async def test_invalid_progress_does_not_write(numeric_service, value):
    service, kr, db = numeric_service
    with pytest.raises(ValueError):
        await service.update_progress(3, 1, value)
    assert kr.current_value is None
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_numeric_cannot_bypass_rules_with_boolean_endpoint(numeric_service):
    service, kr, db = numeric_service
    with pytest.raises(ValueError):
        await service.toggle_achieved(3, 1, True)
    db.add.assert_not_called()


def test_old_record_preserves_original_result_without_fabricating_snapshot():
    record = ProgressRecord(id=1, value=6, is_achieved=True)
    assert record.to_dict()["is_achieved"]
    assert record.to_dict()["target_snapshot"] is None
