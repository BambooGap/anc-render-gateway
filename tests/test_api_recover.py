from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_recover_endpoint_builds_patch_packet() -> None:
    response = client.post(
        "/recover",
        json={
            "failure_record": {
                "category": "topology_dof_violation",
                "signature": "object_rotation_error",
                "raw_signature": "window_flipping_bug",
                "recovery_policy": "LEVEL_2_NEGATIVE_MITIGATION",
                "bad_prompt_fragment_ref": "frag_001",
                "bad_prompt_fragment": "她轻轻推开了推拉窗",
                "suggested_positive_lock": "窗扇始终保持垂直平面姿态，只沿上下轨道做水平滑动。",
                "packet_condition_hash": "hash_001",
            }
        },
    )

    assert response.status_code == 200
    patch = response.json()
    assert patch["recovery_policy"] == "LEVEL_2_NEGATIVE_MITIGATION"
    assert "窗扇保持垂直平面姿态" in patch["patch_prompt"]
    assert patch["locked_regions"]
    assert patch["target_regions"]
