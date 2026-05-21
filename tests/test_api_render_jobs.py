from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _compiled_packet() -> dict[str, object]:
    response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_render", "shot_id": "shot_api_render", "objects": []},
            "render_contract": {"shot_id": "shot_api_render"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_render_job() -> dict[str, object]:
    packet = _compiled_packet()
    response = client.post(
        "/render-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "vendor": "mock",
            "model": "mock-video-v1",
            "metadata": {"seed": 7},
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_get_and_recent_render_jobs() -> None:
    job = _create_render_job()

    assert job["status"] == "PENDING"
    assert job["render_hash"]

    get_response = client.get(f"/render-jobs/{job['job_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["job_id"] == job["job_id"]

    recent_response = client.get("/render-jobs/recent?limit=20")
    assert recent_response.status_code == 200
    recent = recent_response.json()
    assert len(recent) >= 1
    assert recent[0]["job_id"] == job["job_id"]


def test_run_mock_render_job_api() -> None:
    job = _create_render_job()

    response = client.post(f"/render-jobs/{job['job_id']}/run-mock")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"
    assert payload["video_uri"].startswith("mock://renders/")


def test_fail_mock_render_job_api() -> None:
    job = _create_render_job()

    response = client.post(
        f"/render-jobs/{job['job_id']}/fail-mock",
        json={"error_message": "mock timeout"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILED"
    assert payload["error_message"] == "mock timeout"
