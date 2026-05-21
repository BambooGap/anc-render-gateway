import json
from pathlib import Path
from typing import Any

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RenderContract, StateT


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def test_sliding_window_fixture() -> None:
    case = _load_fixture("sliding_window_case.json")
    state = StateT.model_validate(case["state"])
    packet = compile_render_packet(state, RenderContract(shot_id=state.shot_id), case["prompt"])

    for expected in case["contains"]:
        assert expected in packet.compiled_prompt


def test_valve_fixture() -> None:
    case = _load_fixture("valve_case.json")
    state = StateT.model_validate(case["state"])
    packet = compile_render_packet(state, RenderContract(shot_id=state.shot_id), case["prompt"])

    for expected in case["contains"]:
        assert expected in packet.compiled_prompt


def test_negative_trap_fixture() -> None:
    case = _load_fixture("negative_trap_case.json")
    state = StateT.model_validate(case["state"])
    packet = compile_render_packet(state, RenderContract(shot_id=state.shot_id), case["prompt"])

    for expected in case["contains"]:
        assert expected in packet.compiled_prompt
    for forbidden in case["not_contains"]:
        assert forbidden not in packet.compiled_prompt
