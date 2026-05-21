from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, SceneObject, StateT
from anc_gateway.manual.job_manager import complete_manual_job, create_manual_job
from anc_gateway.manual.job_manager import manual_job_to_response
from anc_gateway.manual.schemas import (
    CompleteManualJobRequest,
    ManualJobCreateRequest,
    ManualVendorPlatform,
)
from anc_gateway.render.job_manager import create_render_job, render_job_to_response
from anc_gateway.render.job_manager import submit_render_job_to_vendor
from anc_gateway.render.mock_worker import run_mock_render
from anc_gateway.render.schemas import RenderJobCreateRequest
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.recovery.patch_packet import build_patch_packet
from anc_gateway.storage.database import create_engine_from_url, get_database_url, get_session, init_db
from anc_gateway.storage.repositories import list_recent_failures


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


def init_database() -> None:
    database_url = get_database_url()
    engine = create_engine_from_url(database_url)
    init_db(engine)
    print(f"Initialized database: {database_url}")


def print_recent_failures(limit: int = 20) -> None:
    with get_session() as session:
        records = list_recent_failures(session, limit=limit)
        print(
            json.dumps(
                [
                    {
                        "failure_signature": record.failure_signature,
                        "failure_category": record.failure_category,
                        "bad_prompt_fragment": record.bad_prompt_fragment,
                        "recovery_policy": record.recovery_policy,
                        "created_at": record.created_at.isoformat()
                        if record.created_at
                        else None,
                    }
                    for record in records
                ],
                ensure_ascii=False,
                indent=2,
            )
        )


def mock_render_demo() -> None:
    state = StateT(
        id="state_mock_render_001",
        shot_id="shot_mock_render_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_mock_render_001", ruleset_fingerprint="rc1")
    packet = compile_render_packet(state, contract, "她轻轻推开了推拉窗，风吹进房间。")

    render_request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
    )
    with get_session() as session:
        render_job = create_render_job(session, render_request, request_id="cli-mock-render-demo")
        render_job = run_mock_render(session, render_job)
        render_response = render_job_to_response(render_job)

    audit = RFSAuditResult(
        ok=False,
        raw_signature="window_flipping_bug",
        bad_prompt_fragment_ref="frag_001",
    )
    record = normalize_rfs_failure(audit, packet)
    patch = build_patch_packet(record)

    print("compiled_render_packet:")
    print(json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\nrender_job:")
    print(json.dumps(render_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\nfailure_cache_record:")
    print(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\npatch_packet:")
    print(json.dumps(patch.model_dump(mode="json"), ensure_ascii=False, indent=2))


def vendor_demo() -> None:
    state = StateT(
        id="state_vendor_demo_001",
        shot_id="shot_vendor_demo_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_vendor_demo_001", ruleset_fingerprint="rc1")
    packet = compile_render_packet(state, contract, "她轻轻推开了推拉窗，风吹进房间。")

    render_request = RenderJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        vendor="mock",
    )
    with get_session() as session:
        render_job = create_render_job(session, render_request, request_id="cli-vendor-demo")
        render_job = submit_render_job_to_vendor(session, render_job)
        render_response = render_job_to_response(render_job)

    audit = RFSAuditResult(
        ok=False,
        raw_signature="window_flipping_bug",
        bad_prompt_fragment_ref="frag_001",
    )
    record = normalize_rfs_failure(audit, packet)
    patch = build_patch_packet(record)

    print("vendor_render_job:")
    print(json.dumps(render_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\nexternal_job_id:")
    print(render_job.external_job_id)
    print("\nfailure_cache_record:")
    print(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\npatch_packet:")
    print(json.dumps(patch.model_dump(mode="json"), ensure_ascii=False, indent=2))


def manual_demo() -> None:
    state = StateT(
        id="state_manual_demo_001",
        shot_id="shot_manual_demo_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_manual_demo_001", ruleset_fingerprint="rc1")
    packet = compile_render_packet(state, contract, "她轻轻推开了推拉窗，风吹进房间。")

    manual_request = ManualJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        platform=ManualVendorPlatform.GENERIC_WEB,
    )
    with get_session() as session:
        manual_job = create_manual_job(session, manual_request, request_id="cli-manual-demo")
        manual_job = complete_manual_job(
            session,
            manual_job,
            CompleteManualJobRequest(
                result_video_uri="file:///tmp/mock_video.mp4",
                user_notes="Manual demo completed with a local mock file.",
            ),
        )
        manual_response = manual_job_to_response(manual_job)

    audit = RFSAuditResult(
        ok=False,
        raw_signature="window_flipping_bug",
        bad_prompt_fragment_ref="frag_001",
    )
    record = normalize_rfs_failure(audit, packet)
    patch = build_patch_packet(record)

    print("manual_job:")
    print(json.dumps(manual_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\ncopy_instructions:")
    print(manual_response.copy_instructions)
    print("\nfailure_cache_record:")
    print(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\npatch_packet:")
    print(json.dumps(patch.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="anc-gateway")
    parser.add_argument(
        "command",
        choices=[
            "demo-sliding-window",
            "init-db",
            "manual-demo",
            "mock-render-demo",
            "recent-failures",
            "serve",
            "vendor-demo",
        ],
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    if args.command == "demo-sliding-window":
        demo_sliding_window()
    elif args.command == "init-db":
        init_database()
    elif args.command == "manual-demo":
        manual_demo()
    elif args.command == "mock-render-demo":
        mock_render_demo()
    elif args.command == "recent-failures":
        print_recent_failures(limit=args.limit)
    elif args.command == "serve":
        serve()
    elif args.command == "vendor-demo":
        vendor_demo()


if __name__ == "__main__":
    main()
