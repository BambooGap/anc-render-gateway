from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from anc_gateway.attempts.export import export_case_markdown
from anc_gateway.attempts.job_manager import (
    attempt_to_response,
    case_to_response,
    create_attempt,
    create_case,
    link_attempt_manual_audit,
    link_attempt_manual_job,
    link_attempt_patch,
    list_case_attempts,
)
from anc_gateway.attempts.schemas import AttemptCreateRequest, CaseCreateRequest
from anc_gateway.audit.manual_audit import build_rfs_audit_from_manual_request
from anc_gateway.audit.schemas import ManualAuditCreateRequest
from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import FailureCacheRecord, PatchPacket, RFSAuditResult, RenderContract, SceneObject, StateT
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
from anc_gateway.storage.repositories import (
    list_recent_failures,
    save_failure_record,
    save_manual_audit,
    save_patch_record,
)
from anc_gateway.casebase.search import search_casebase
from anc_gateway.casebase.stats import get_failure_signature_stats
from anc_gateway.casebase.recommendations import recommend_patches
from anc_gateway.casebase.schemas import RecommendRequest
from anc_gateway.recovery.context import infer_object_context


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


def console() -> None:
    print("ANC Web Console:")
    print("http://127.0.0.1:8000/console")
    serve()


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


def manual_audit_demo() -> None:
    state = StateT(
        id="state_manual_audit_demo_001",
        shot_id="shot_manual_audit_demo_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_manual_audit_demo_001", ruleset_fingerprint="rc1")
    packet = compile_render_packet(state, contract, "她轻轻推开了推拉窗，风吹进房间。")

    manual_request = ManualJobCreateRequest(
        condition_hash=packet.condition_hash,
        compiled_prompt=packet.compiled_prompt,
        source_map=packet.source_map,
        platform=ManualVendorPlatform.GENERIC_WEB,
    )
    with get_session() as session:
        manual_job = create_manual_job(session, manual_request, request_id="cli-manual-audit-demo")
        manual_job = complete_manual_job(
            session,
            manual_job,
            CompleteManualJobRequest(
                result_video_uri="file:///tmp/mock_video.mp4",
                user_notes="Manual audit demo completed with a local mock file.",
            ),
        )
        manual_response = manual_job_to_response(manual_job)

        audit_request = ManualAuditCreateRequest(
            manual_job_id=manual_job.id,
            bad_prompt_fragment_ref="frag_001",
            failure_type="window_flipping_bug",
            notes="窗户被生成成向外翻转。",
        )
        audit = build_rfs_audit_from_manual_request(audit_request)
        record = normalize_rfs_failure(audit, packet)
        failure = save_failure_record(
            session,
            record,
            audit,
            condition_hash=packet.condition_hash,
            ruleset_fingerprint=packet.ruleset_fingerprint,
            request_id="cli-manual-audit-demo",
        )
        manual_audit = save_manual_audit(
            session,
            request_id="cli-manual-audit-demo",
            manual_job_id=manual_job.id,
            render_job_id=None,
            condition_hash=packet.condition_hash,
            bad_prompt_fragment_ref="frag_001",
            raw_failure_type=audit_request.failure_type,
            failure_signature=record.signature,
            failure_category=record.category,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=audit_request.notes,
            rfs_scores=audit.details["rfs_scores"],
        )

    patch = build_patch_packet(record)

    print("manual_job:")
    print(json.dumps(manual_response.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print("\nmanual_audit:")
    print(
        json.dumps(
            {
                "audit_id": manual_audit.id,
                "failure_record_id": failure.id,
                "failure_signature": record.raw_signature,
                "normalized_failure_signature": record.signature,
                "failure_category": record.category,
                "recovery_policy": record.recovery_policy,
                "suggested_positive_lock": record.suggested_positive_lock,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("\npatch_packet:")
    print(json.dumps(patch.model_dump(mode="json"), ensure_ascii=False, indent=2))


def attempt_loop_demo() -> None:
    state = StateT(
        id="state_attempt_loop_demo_001",
        shot_id="shot_attempt_loop_demo_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_attempt_loop_demo_001", ruleset_fingerprint="rc1")
    raw_prompt = "她轻轻推开了推拉窗，冷白色应急灯照进房间，窗外有细小尘埃缓慢漂浮。"
    packet = compile_render_packet(state, contract, raw_prompt)

    with get_session() as session:
        case = create_case(
            session,
            CaseCreateRequest(raw_prompt=raw_prompt, title="sliding-window-attempt-loop"),
            request_id="cli-attempt-loop-demo",
        )
        attempt_1 = create_attempt(
            session,
            case,
            AttemptCreateRequest(
                raw_prompt=raw_prompt,
                compiled_prompt=packet.compiled_prompt,
                condition_hash=packet.condition_hash,
                source_map=packet.source_map,
            ),
            request_id="cli-attempt-loop-demo",
        )

        manual_job = create_manual_job(
            session,
            ManualJobCreateRequest(
                condition_hash=packet.condition_hash,
                compiled_prompt=packet.compiled_prompt,
                source_map=packet.source_map,
                platform=ManualVendorPlatform.GENERIC_WEB,
            ),
            request_id="cli-attempt-loop-demo",
        )
        manual_job = complete_manual_job(
            session,
            manual_job,
            CompleteManualJobRequest(result_video_uri="file:///tmp/attempt_loop_demo.mp4"),
        )
        attempt_1 = link_attempt_manual_job(
            session,
            attempt_1,
            manual_job_id=manual_job.id,
            result_video_uri=manual_job.result_video_uri,
        )

        audit_request = ManualAuditCreateRequest(
            manual_job_id=manual_job.id,
            bad_prompt_fragment_ref="frag_001",
            failure_type="window_flipping_bug",
        )
        audit = build_rfs_audit_from_manual_request(audit_request)
        record = normalize_rfs_failure(audit, packet)
        failure = save_failure_record(
            session,
            record,
            audit,
            condition_hash=packet.condition_hash,
            ruleset_fingerprint=packet.ruleset_fingerprint,
            request_id="cli-attempt-loop-demo",
        )
        manual_audit = save_manual_audit(
            session,
            request_id="cli-attempt-loop-demo",
            manual_job_id=manual_job.id,
            render_job_id=None,
            condition_hash=packet.condition_hash,
            bad_prompt_fragment_ref="frag_001",
            raw_failure_type=audit_request.failure_type,
            failure_signature=record.signature,
            failure_category=record.category,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=audit_request.notes,
            rfs_scores=audit.details["rfs_scores"],
        )
        attempt_1 = link_attempt_manual_audit(
            session,
            attempt_1,
            manual_audit_id=manual_audit.id,
            failure_record_id=failure.id,
        )

        patch = build_patch_packet(record)
        attempt_1 = link_attempt_patch(session, attempt_1, patch_prompt=patch.patch_prompt)
        attempt_2 = create_attempt(
            session,
            case,
            AttemptCreateRequest(previous_attempt_id=attempt_1.id, patch_packet=patch),
            request_id="cli-attempt-loop-demo",
        )

        print("case:")
        print(json.dumps(case_to_response(case).model_dump(mode="json"), ensure_ascii=False, indent=2))
        print("\nattempt_1:")
        print(json.dumps(attempt_to_response(attempt_1).model_dump(mode="json"), ensure_ascii=False, indent=2))
        print("\npatch_packet:")
        print(json.dumps(patch.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print("\nattempt_2:")
        print(json.dumps(attempt_to_response(attempt_2).model_dump(mode="json"), ensure_ascii=False, indent=2))


def export_case_demo() -> None:
    state = StateT(
        id="state_export_case_demo_001",
        shot_id="shot_export_case_demo_001",
        objects=[
            SceneObject(
                id="window_01",
                name="推拉窗",
                object_type="sliding_window",
                topology={"dof": "horizontal_slide", "rail": "上下轨道"},
            )
        ],
    )
    contract = RenderContract(shot_id="shot_export_case_demo_001", ruleset_fingerprint="rc1")
    raw_prompt = "她轻轻推开了推拉窗，冷白色应急灯照进房间。"
    packet = compile_render_packet(state, contract, raw_prompt)

    with get_session() as session:
        case = create_case(
            session,
            CaseCreateRequest(raw_prompt=raw_prompt, title="export-case-demo"),
            request_id="cli-export-case-demo",
        )
        attempt_1 = create_attempt(
            session,
            case,
            AttemptCreateRequest(
                raw_prompt=raw_prompt,
                compiled_prompt=packet.compiled_prompt,
                condition_hash=packet.condition_hash,
                source_map=packet.source_map,
            ),
            request_id="cli-export-case-demo",
        )
        audit_request = ManualAuditCreateRequest(
            bad_prompt_fragment_ref="frag_001",
            failure_type="window_flipping_bug",
        )
        audit = build_rfs_audit_from_manual_request(audit_request)
        record = normalize_rfs_failure(audit, packet)
        failure = save_failure_record(
            session,
            record,
            audit,
            condition_hash=packet.condition_hash,
            ruleset_fingerprint=packet.ruleset_fingerprint,
            request_id="cli-export-case-demo",
        )
        manual_audit = save_manual_audit(
            session,
            request_id="cli-export-case-demo",
            manual_job_id=None,
            render_job_id=None,
            condition_hash=packet.condition_hash,
            bad_prompt_fragment_ref="frag_001",
            raw_failure_type=audit_request.failure_type,
            failure_signature=record.signature,
            failure_category=record.category,
            recovery_policy=record.recovery_policy,
            suggested_positive_lock=record.suggested_positive_lock,
            notes=audit_request.notes,
            rfs_scores=audit.details["rfs_scores"],
        )
        attempt_1 = link_attempt_manual_audit(
            session,
            attempt_1,
            manual_audit_id=manual_audit.id,
            failure_record_id=failure.id,
        )
        patch = build_patch_packet(record)
        patch_record = save_patch_record(
            session,
            patch,
            failure_record_id=failure.id,
            request_id="cli-export-case-demo",
        )
        attempt_1 = link_attempt_patch(
            session,
            attempt_1,
            patch_prompt=patch.patch_prompt,
            patch_record_id=patch_record.id,
        )
        create_attempt(
            session,
            case,
            AttemptCreateRequest(previous_attempt_id=attempt_1.id, patch_packet=patch),
            request_id="cli-export-case-demo",
        )
        markdown = export_case_markdown(case, list_case_attempts(session, case.id))
        print("\n".join(markdown.splitlines()[:24]))


def casebase_demo() -> None:
    with get_session() as session:
        # 1. Failure signature stats
        stats = get_failure_signature_stats(session)
        print("=== Failure Signature Stats ===")
        print(
            json.dumps(
                [s.model_dump(mode="json") for s in stats],
                ensure_ascii=False,
                indent=2,
            )
        )

        # 2. Search by text
        search_results = search_casebase(session, q="推拉窗", limit=5)
        print("\n=== Search: q='推拉窗' ===")
        print(
            json.dumps(
                [r.model_dump(mode="json") for r in search_results],
                ensure_ascii=False,
                indent=2,
            )
        )

        # 3. Search by failure signature
        if stats:
            sig = stats[0].failure_signature
            sig_results = search_casebase(session, failure_signature=sig, limit=5)
            print(f"\n=== Search: failure_signature='{sig}' ===")
            print(
                json.dumps(
                    [r.model_dump(mode="json") for r in sig_results],
                    ensure_ascii=False,
                    indent=2,
                )
            )

            # 4. Recommend patches
            request = RecommendRequest(failure_signature=sig, limit=3)
            recommendations = recommend_patches(session, request)
            print(f"\n=== Recommend Patches: failure_signature='{sig}' ===")
            print(json.dumps(recommendations.model_dump(mode="json"), ensure_ascii=False, indent=2))


def patch_context_demo() -> None:
    scenarios = [
        {
            "name": "sliding_window",
            "failure_signature": "object_rotation_error",
            "bad_prompt_fragment": "她轻轻推开了推拉窗，风吹进房间。",
        },
        {
            "name": "valve",
            "failure_signature": "object_rotation_error",
            "bad_prompt_fragment": "她顺时针旋转阀门，水流逐渐变小。",
        },
        {
            "name": "hinged_door",
            "failure_signature": "object_rotation_error",
            "bad_prompt_fragment": "她握住门把手，将门板向外推开。",
        },
        {
            "name": "drawer",
            "failure_signature": "object_rotation_error",
            "bad_prompt_fragment": "她握住抽屉把手，将抽屉从滑轨中拉出。",
        },
        {
            "name": "button_panel",
            "failure_signature": "hand_panel_misalignment",
            "bad_prompt_fragment": "她的手指悬停在按钮面板上方，没有按下。",
        },
        {
            "name": "extra_limb",
            "failure_signature": "extra_limb_generated",
            "bad_prompt_fragment": "她用三只手同时抓住了绳子。",
        },
        {
            "name": "visual_anchor",
            "failure_signature": "visual_anchor_ignored",
            "bad_prompt_fragment": "红色的裙子被生成成了蓝色，参考图场景跳变。",
        },
    ]

    patches: list[tuple[str, PatchPacket]] = []
    for s in scenarios:
        ctx = infer_object_context(
            failure_signature=s["failure_signature"],
            bad_prompt_fragment=s["bad_prompt_fragment"],
        )
        record = FailureCacheRecord(
            category="topology_dof_violation",
            signature=s["failure_signature"],
            raw_signature=s["failure_signature"],
            recovery_policy="LEVEL_2_NEGATIVE_MITIGATION",
            bad_prompt_fragment_ref="frag_001",
            bad_prompt_fragment=s["bad_prompt_fragment"],
            suggested_positive_lock="",
            packet_condition_hash="demo",
        )
        patch = build_patch_packet(record)
        patches.append((s["name"], patch))

        print(f"\n=== {s['name']} ===")
        print(f"  object_type:  {ctx.object_type}")
        print(f"  motion_model: {ctx.motion_model}")
        print(f"  confidence:   {ctx.confidence}")
        print(f"  patch_prompt: {patch.patch_prompt[:80]}...")
        print(f"  positive_lock: {patch.positive_lock[:80]}...")

    # Verify patches are not all identical
    prompts = [p.patch_prompt for _, p in patches]
    unique_prompts = len(set(prompts))
    print("\n=== Summary ===")
    print(f"  Scenarios: {len(patches)}")
    print(f"  Unique patch_prompts: {unique_prompts}/{len(patches)}")
    print(f"  All identical: {'YES - PROBLEM!' if unique_prompts == 1 else 'NO - GOOD'}")


def casebase_ranking_demo() -> None:
    """Demo: show ranking and dedup in casebase recommendations."""
    from anc_gateway.recovery.patch_packet import build_patch_packet
    from anc_gateway.storage.repositories import save_failure_record, save_patch_record

    with get_session() as session:
        # Create multiple cases with different object types
        scenarios = [
            ("sliding_window_case", "她轻轻推开了推拉窗。", "window_flipping_bug"),
            ("valve_case", "她顺时针旋转阀门，水流变小。", "window_flipping_bug"),
            ("drawer_case", "她将抽屉从滑轨中拉出。", "window_flipping_bug"),
            ("custom_case", "场景光线不一致。", "custom"),
        ]

        for title, raw_prompt, failure_type in scenarios:
            packet = compile_render_packet(
                StateT(id=f"state_{title}", shot_id=f"shot_{title}"),
                RenderContract(shot_id=f"shot_{title}"),
                raw_prompt,
            )
            audit = RFSAuditResult(ok=False, raw_signature=failure_type, bad_prompt_fragment_ref="frag_001")
            record = normalize_rfs_failure(audit, packet)
            failure = save_failure_record(
                session, record, audit,
                condition_hash=packet.condition_hash,
                ruleset_fingerprint=packet.ruleset_fingerprint,
                request_id=f"cli-ranking-{title}",
            )
            patch = build_patch_packet(record)
            save_patch_record(session, patch, failure_record_id=failure.id, request_id=f"cli-ranking-{title}")

        session.commit()

        # Now recommend for valve context
        request = RecommendRequest(
            failure_signature="object_rotation_error",
            bad_prompt_fragment="她双手握住圆形阀门，沿中心轴旋转",
            object_type="valve",
            motion_model="center_axis_rotation",
            limit=5,
        )
        response = recommend_patches(session, request)

        print("=== Casebase Ranking Demo ===")
        print(f"Query: failure_signature={request.failure_signature}")
        print(f"       object_type={request.object_type}")
        print(f"       motion_model={request.motion_model}")
        print(f"\nTotal candidates (before dedup): {response.total_candidates}")
        print(f"Recommended patches (after dedup): {len(response.recommended_patches)}")

        for i, p in enumerate(response.recommended_patches):
            print(f"\n[{i+1}] ranking_score={p.ranking_score:.2f}")
            print(f"    failure_signature: {p.failure_signature}")
            print(f"    object_type: {p.object_type}")
            print(f"    motion_model: {p.motion_model}")
            print(f"    matched_by: {p.matched_by}")
            print(f"    duplicate_count: {p.duplicate_count}")
            print(f"    reason: {p.reason}")
            prompt = p.patch_prompt or ""
            print(f"    patch_prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="anc-gateway")
    parser.add_argument(
        "command",
        choices=[
            "demo-sliding-window",
            "init-db",
            "manual-audit-demo",
            "manual-demo",
            "mock-render-demo",
            "recent-failures",
            "serve",
            "console",
            "attempt-loop-demo",
            "casebase-demo",
            "casebase-ranking-demo",
            "export-case-demo",
            "patch-context-demo",
            "vendor-demo",
        ],
    )
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    if args.command == "demo-sliding-window":
        demo_sliding_window()
    elif args.command == "console":
        console()
    elif args.command == "attempt-loop-demo":
        attempt_loop_demo()
    elif args.command == "casebase-demo":
        casebase_demo()
    elif args.command == "casebase-ranking-demo":
        casebase_ranking_demo()
    elif args.command == "export-case-demo":
        export_case_demo()
    elif args.command == "patch-context-demo":
        patch_context_demo()
    elif args.command == "init-db":
        init_database()
    elif args.command == "manual-audit-demo":
        manual_audit_demo()
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
