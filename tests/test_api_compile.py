from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_compile_endpoint_returns_packet_with_source_map_and_hash() -> None:
    response = client.post(
        "/compile",
        json={
            "state": {
                "id": "state_api_compile",
                "shot_id": "shot_api_compile",
                "objects": [
                    {
                        "id": "window_01",
                        "name": "推拉窗",
                        "object_type": "sliding_window",
                        "topology": {"dof": "horizontal_slide"},
                    }
                ],
            },
            "render_contract": {
                "shot_id": "shot_api_compile",
                "ruleset_fingerprint": "rc-api",
            },
            "raw_prompt": "她轻轻推开了推拉窗，风吹进房间。",
        },
    )

    assert response.status_code == 200
    packet = response.json()
    assert "上下轨道" in packet["compiled_prompt"]
    assert "水平滑动" in packet["compiled_prompt"]
    assert packet["condition_hash"]
    assert "frag_001" in packet["source_map"]["fragments"]
