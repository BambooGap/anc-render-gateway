from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, SceneObject, StateT
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.recovery.patch_packet import build_patch_packet


def demo_sliding_window() -> None:
    state = StateT(
        id="state_demo_001",
        shot_id="shot_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_001", ruleset_fingerprint="rc1")
    packet = compile_render_packet(state, contract, "她轻轻推开了推拉窗，风吹进房间。")

    audit = RFSAuditResult(
        ok=False,
        raw_signature="window_flipping_bug",
        bad_prompt_fragment_ref="frag_001",
    )
    record = normalize_rfs_failure(audit, packet)
    patch = build_patch_packet(record)

    print("compiled_prompt:")
    print(packet.compiled_prompt)
    print("\nsource_map:")
    print(json.dumps(packet.source_map.model_dump(), ensure_ascii=False, indent=2))
    print("\nfailure_cache_record:")
    print(json.dumps(record.model_dump(), ensure_ascii=False, indent=2))
    print("\npatch_packet:")
    print(json.dumps(patch.model_dump(), ensure_ascii=False, indent=2))


def serve() -> None:
    import uvicorn

    uvicorn.run("anc_gateway.api.app:app", host="127.0.0.1", port=8000, reload=True)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="anc-gateway")
    parser.add_argument("command", choices=["demo-sliding-window", "serve"])
    args = parser.parse_args(argv)

    if args.command == "demo-sliding-window":
        demo_sliding_window()
    elif args.command == "serve":
        serve()


if __name__ == "__main__":
    main()
