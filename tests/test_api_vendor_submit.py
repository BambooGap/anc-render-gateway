import json

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.storage.database import get_session
from anc_gateway.storage.models import RenderJobModel


client = TestClient(app)


def _create_render_job() -> dict[str, object]:
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_vendor", "shot_id": "shot_api_vendor", "objects": []},
            "render_contract": {"shot_id": "shot_api_vendor"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()
    render_response = client.post(
        "/render-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "vendor": "mock",
            "model": "mock-video-v1",
        },
    )
    assert render_response.status_code == 200
    return render_response.json()


def test_submit_vendor_updates_render_job_to_succeeded() -> None:
    job = _create_render_job()

    response = client.post(f"/render-jobs/{job['job_id']}/submit-vendor")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"
    assert payload["video_uri"].startswith("mock://renders/")

    with get_session() as session:
        stored_job = session.get(RenderJobModel, payload["job_id"])
        assert stored_job is not None
        assert stored_job.external_job_id is not None
        assert stored_job.external_job_id.startswith("mock_external_")
        metadata = json.loads(stored_job.metadata_json)
        assert metadata["external_job_id"] == stored_job.external_job_id
        assert metadata["vendor_submit_raw_response"]["vendor"] == "mock"


def test_submit_vendor_can_use_fake_http_adapter(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("FAKE_HTTP_API_KEY", "fake-secret")
    compile_response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_fake_http", "shot_id": "shot_api_fake_http", "objects": []},
            "render_contract": {"shot_id": "shot_api_fake_http"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert compile_response.status_code == 200
    packet = compile_response.json()
    render_response = client.post(
        "/render-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "vendor": "fake-http",
            "model": "fake-http-video-v1",
        },
    )
    assert render_response.status_code == 200
    job = render_response.json()

    submit_response = client.post(f"/render-jobs/{job['job_id']}/submit-vendor")

    assert submit_response.status_code == 200
    payload = submit_response.json()
    assert payload["status"] == "SUCCEEDED"
    assert payload["video_uri"].startswith("fake-http://renders/")
