from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _create_attempt_with_patch() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    case = client.post(
        "/cases",
        json={"title": "Next attempt case", "raw_prompt": "她推开推拉窗。"},
    ).json()
    attempt = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={"raw_prompt": "她推开推拉窗。"},
    ).json()
    patch = {"patch_prompt": "窗扇只沿上下轨道水平滑动，不翻转。"}
    linked = client.post(
        f"/attempts/{attempt['attempt_id']}/patch",
        json={"patch_packet": patch, "patch_record_id": "patch_record_test"},
    ).json()
    return case, linked, patch


def test_attempt_next_api_creates_next_attempt_from_patch_packet() -> None:
    _, attempt, patch = _create_attempt_with_patch()

    response = client.post(
        f"/attempts/{attempt['attempt_id']}/next",
        json={"patch_packet": patch},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["attempt_index"] == 2
    assert payload["status"] == "DRAFT"
    assert "窗扇只沿上下轨道水平滑动" in payload["raw_prompt"]


def test_attempt_next_api_uses_stored_patch_and_deduplicates_constraint() -> None:
    _, attempt, patch = _create_attempt_with_patch()
    first_next = client.post(
        f"/attempts/{attempt['attempt_id']}/next",
        json={"patch_packet": patch},
    ).json()

    response = client.post(
        f"/attempts/{first_next['attempt_id']}/next",
        json={"patch_packet": patch},
    )

    assert response.status_code == 200
    raw_prompt = response.json()["raw_prompt"]
    assert raw_prompt.count("窗扇只沿上下轨道水平滑动") == 1
