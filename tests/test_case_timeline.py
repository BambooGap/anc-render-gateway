from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_case_timeline_returns_attempts_ordered_by_attempt_index() -> None:
    case = client.post(
        "/cases",
        json={"title": "Timeline case", "raw_prompt": "她推开推拉窗。"},
    ).json()
    attempt_1 = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={"raw_prompt": "她推开推拉窗。", "condition_hash": "hash_1"},
    ).json()
    patch = {"positive_lock": "窗扇保持垂直，只水平滑动。"}
    attempt_2 = client.post(
        f"/attempts/{attempt_1['attempt_id']}/next",
        json={"patch_packet": patch},
    ).json()

    response = client.get(f"/cases/{case['case_id']}/timeline")

    assert response.status_code == 200
    timeline = response.json()
    assert [item["attempt_index"] for item in timeline] == [1, 2]
    assert timeline[0]["type"] == "attempt"
    assert timeline[0]["attempt_id"] == attempt_1["attempt_id"]
    assert timeline[1]["attempt_id"] == attempt_2["attempt_id"]
    assert timeline[0]["condition_hash"] == "hash_1"
