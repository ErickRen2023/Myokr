import os
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest


pytestmark = pytest.mark.skipif(os.getenv("OKR_LIVE_TEST") != "1", reason="Requires running local OKR and aSSO services")


def test_numeric_rules_through_real_sso_and_http():
    httpx = pytest.importorskip("httpx")
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        response = client.post("http://localhost:8000/api/auth/login", json={
            "username": os.environ["SSO_TEST_USERNAME"], "password": os.environ["SSO_TEST_PASSWORD"],
        })
        assert response.status_code == 200, f"SSO login returned {response.status_code}"
        session = response.cookies.get("session_id")
        assert session
        response = client.get("http://localhost:8001/api/auth/sso/login")
        assert response.status_code == 302
        authorization = parse_qs(urlparse(response.headers["location"]).query)
        params = {key: values[0] for key, values in authorization.items()}
        response = client.get("http://localhost:8000/oauth/authorize", params=params, headers={"Cookie": f"session_id={session}"})
        if response.status_code == 200:
            assert response.json()["data"]["action"] == "consent"
            response = client.post("http://localhost:8000/oauth/authorize", data={**params, "action": "approve"}, headers={"Cookie": f"session_id={session}"})
        assert response.status_code == 302
        callback = response.headers["location"]
        assert urlparse(callback).hostname == "localhost"
        response = client.get(callback)
        assert response.status_code == 302
        assert "error=" not in response.headers["location"], "SSO callback failed"
        result = client.get("http://localhost:8001/api/auth/sso/result").json()["data"]
        assert result["status"] == "authenticated"
        client.headers["Authorization"] = f"Bearer {result['token']}"

        def request(method, path, **kwargs):
            response = client.request(method, f"http://localhost:8001/api{path}", **kwargs)
            assert response.status_code == 200, f"{path}: HTTP {response.status_code}"
            body = response.json()
            assert body["code"] == 0, f"{path}: {body['message']}"
            return body["data"]

        cycle = request("POST", "/cycles/create", json={"type": 1, "start_date": "2026-10-01", "end_date": "2026-10-31"})
        try:
            objective = request("POST", "/objectives/create", json={"cycle_id": cycle["id"], "title": f"Issue 17 联调 {uuid4().hex[:8]}"})
            upper = request("POST", "/key-results/create", json={"objective_id": objective["id"], "title": "晚睡不超过10天", "type": 1, "target": {"value": 10, "unit": "天", "operator": "lte"}})
            legacy = request("POST", "/key-results/create", json={"objective_id": objective["id"], "title": "至少阅读10天", "type": 1, "target": {"value": 10, "unit": "天"}})
            assert upper["current_value"] is None and not upper["is_achieved"]
            assert legacy["target"]["operator"] == "gte"
            for value, achieved in [(0, True), (6, True), (10, True), (11, False), (6, True)]:
                updated = request("POST", "/key-results/update-progress", json={"id": upper["id"], "value": value})
                assert updated["is_achieved"] is achieved
                dashboard = request("GET", "/dashboard", params={"cycle_id": cycle["id"]})
                dashboard_kr = next(kr for kr in dashboard["objectives"][0]["key_results"] if kr["id"] == upper["id"])
                assert dashboard_kr == updated
                assert dashboard["summary"]["completed_key_results"] == int(achieved)
                assert dashboard["summary"]["average_kr_progress"] == (50 if achieved else 0)

            request("POST", "/key-results/update-progress", json={"id": legacy["id"], "value": 6})
            updated = request("POST", "/key-results/update", json={"id": upper["id"], "target": {"value": 5, "unit": "天"}})
            assert updated["target"]["operator"] == "lte" and not updated["is_achieved"]
            records = request("GET", "/progress-records", params={"key_result_id": upper["id"]})["records"]
            assert records[0]["target_snapshot"]["value"] == 5
            assert not records[0]["is_achieved"]
            assert records[1]["target_snapshot"]["value"] == 10 and records[1]["is_achieved"]
            updated = request("POST", "/key-results/update", json={"id": upper["id"], "target": {"operator": "gte"}})
            assert updated["is_achieved"]
            updated = request("POST", "/key-results/update", json={"id": upper["id"], "target": {"operator": "lte", "value": 0}})
            assert not updated["is_achieved"]
            updated = request("POST", "/key-results/update-progress", json={"id": upper["id"], "value": 0})
            assert updated["is_achieved"] and updated["usage_percent"] is None
            for path, payload in [("/key-results/update", {"id": upper["id"], "target": {"operator": "lt"}}), ("/key-results/update-progress", {"id": upper["id"], "value": -1}), ("/key-results/toggle-achieved", {"id": upper["id"], "is_achieved": 1})]:
                assert client.post(f"http://localhost:8001/api{path}", json=payload).status_code == 400
            request("POST", "/cycles/review-and-archive", json={"cycle_id": cycle["id"], "summary": "Issue 17 自动回归：上限、兼容、快照、SSO"})
            history = request("GET", "/history/objectives", params={"cycle_id": cycle["id"]})["objectives"][0]
            archived = next(kr for kr in history["key_results"] if kr["id"] == upper["id"])
            assert archived["status"] == 1 and archived["is_achieved"]
            assert archived["target"] == {"operator": "lte", "value": 0, "unit": "天"}
            assert request("GET", "/progress-records", params={"key_result_id": upper["id"]})["records"][-1]["target_snapshot"]["value"] == 10
        finally:
            request("POST", "/cycles/archive", json={"id": cycle["id"]})
