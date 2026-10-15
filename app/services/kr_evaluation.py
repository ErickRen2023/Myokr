from math import isfinite
from typing import Optional


def validate_numeric_target(target: dict) -> dict:
    operator = target.get("operator", "gte")
    value = target.get("value")
    unit = target.get("unit")
    if operator not in ("gte", "lte"):
        raise ValueError("达成规则必须为至少达到或不超过")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("请输入有效的目标值")
    if value < 0 or (operator == "gte" and value == 0):
        raise ValueError("至少达到的目标值必须为正数，不超过的目标值不能为负数")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("单位不能为空")
    return {**target, "operator": operator, "value": value, "unit": unit.strip()}


def evaluate_numeric(target: dict, current_value: Optional[float]) -> dict:
    if current_value is None:
        return {"progress": 0.0, "is_achieved": False, "usage_percent": None}
    target_value = target.get("value", 1)
    if target.get("operator", "gte") == "lte":
        achieved = current_value <= target_value
        usage = round(current_value / target_value * 100, 1) if target_value > 0 else None
        return {"progress": 100.0 if achieved else 0.0, "is_achieved": achieved, "usage_percent": usage}
    progress = round(min(current_value / (target_value or 1) * 100, 100), 1)
    return {"progress": progress, "is_achieved": target_value > 0 and current_value >= target_value, "usage_percent": None}


def evaluate_kr(kr, milestones=None) -> dict:
    if kr.type == 1:
        return evaluate_numeric(kr.target or {}, kr.current_value)
    if kr.type == 2:
        milestones = milestones or []
        completed = sum(bool(milestone.completed) for milestone in milestones)
        return {
            "progress": round(completed / len(milestones) * 100) if milestones else 0,
            "is_achieved": bool(milestones) and completed == len(milestones),
            "usage_percent": None,
        }
    return {"progress": 100.0 if kr.is_achieved else 0.0, "is_achieved": bool(kr.is_achieved), "usage_percent": None}
