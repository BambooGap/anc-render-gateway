from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def _compiled_packet() -> dict[str, object]:
    response = client.post(
        "/compile",
        json={
            "state": {"id": "state_api_manual", "shot_id": "shot_api_manual", "objects": []},
            "render_contract": {"shot_id": "shot_api_manual"},
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_manual_job() -> dict[str, object]:
    packet = _compiled_packet()
    response = client.post(
        "/manual-jobs",
        json={
            "condition_hash": packet["condition_hash"],
            "compiled_prompt": packet["compiled_prompt"],
            "source_map": packet["source_map"],
            "platform": "generic_web",
            "visual_anchor_uri": "file:///tmp/anchor.png",
            "notes": "manual api test",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_api_create_get_complete_fail_and_recent_manual_jobs() -> None:
    job = _create_manual_job()

    assert job["status"] == "WAITING_FOR_USER"
    assert "复制" in job["copy_instructions"] or "Prompt" in job["copy_instructions"]
    assert job["compiled_prompt"] in job["copy_instructions"]

    get_response = client.get(f"/manual-jobs/{job['manual_job_id']}")
    assert get_response.status_code == 200
    assert get_response.json()["manual_job_id"] == job["manual_job_id"]

    complete_response = client.post(
        f"/manual-jobs/{job['manual_job_id']}/complete",
        json={
            "result_video_uri": "file:///tmp/manual_result.mp4",
            "user_notes": "completed by hand",
        },
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "COMPLETED"
    assert completed["result_video_uri"] == "file:///tmp/manual_result.mp4"

    recent_response = client.get("/manual-jobs/recent?limit=20")
    assert recent_response.status_code == 200
    assert len(recent_response.json()) == 1

    failed_job = _create_manual_job()
    fail_response = client.post(
        f"/manual-jobs/{failed_job['manual_job_id']}/fail",
        json={"user_notes": "manual generation failed"},
    )
    assert fail_response.status_code == 200
    assert fail_response.json()["status"] == "FAILED"
