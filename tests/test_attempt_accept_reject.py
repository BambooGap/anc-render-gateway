from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _create_attempt() -> tuple[dict[str, object], dict[str, object]]:
    case = client.post(
        "/cases",
        json={"title": "Accept reject case", "raw_prompt": "基础提示词"},
    ).json()
    attempt = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={"raw_prompt": "基础提示词"},
    ).json()
    return case, attempt


def test_accept_attempt_marks_attempt_and_case_accepted() -> None:
    case, attempt = _create_attempt()

    response = client.post(
        f"/attempts/{attempt['attempt_id']}/accept",
        json={"accept_case": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACCEPTED"
    case_response = client.get(f"/cases/{case['case_id']}")
    assert case_response.status_code == 200
    assert case_response.json()["status"] == "ACCEPTED"


def test_reject_attempt_marks_attempt_rejected_and_saves_notes() -> None:
    _, attempt = _create_attempt()

    response = client.post(
        f"/attempts/{attempt['attempt_id']}/reject",
        json={"notes": "构图漂移，拒绝这一轮。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"FAILED", "REJECTED"}
    assert payload["notes"] == "构图漂移，拒绝这一轮。"
