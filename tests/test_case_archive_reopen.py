from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_archive_and_reopen_case_status() -> None:
    case_response = client.post(
        "/cases",
        json={"title": "Archive case", "raw_prompt": "基础提示词"},
    )
    assert case_response.status_code == 200
    case = case_response.json()

    archive_response = client.post(f"/cases/{case['case_id']}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "ARCHIVED"

    reopen_response = client.post(f"/cases/{case['case_id']}/reopen")
    assert reopen_response.status_code == 200
    assert reopen_response.json()["status"] == "ACTIVE"
