import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "api"


def _load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def test_compile_contract_fixture_passes() -> None:
    response = client.post("/compile", json=_load_fixture("compile_request_sliding_window.json"))

    assert response.status_code == 200
    assert "上下轨道" in response.json()["compiled_prompt"]


def test_audit_contract_fixture_passes() -> None:
    response = client.post("/audit", json=_load_fixture("audit_request_window_flip.json"))

    assert response.status_code == 200
    assert response.json()["signature"] == "object_rotation_error"


def test_recover_contract_fixture_passes() -> None:
    response = client.post("/recover", json=_load_fixture("recover_request_object_rotation_error.json"))

    assert response.status_code == 200
    assert "窗扇保持垂直平面姿态" in response.json()["patch_prompt"]
