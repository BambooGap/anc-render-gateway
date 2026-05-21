from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, StateT
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure
from anc_gateway.storage.database import get_session
from anc_gateway.storage.repositories import list_recent_failures, save_failure_record


def test_save_failure_record_and_list_recent_failures() -> None:
    packet = compile_render_packet(
        StateT(id="state_storage_failure", shot_id="shot_storage_failure"),
        RenderContract(shot_id="shot_storage_failure"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )
    audit = RFSAuditResult(
        ok=False,
        raw_signature="window_flipping_bug",
        bad_prompt_fragment_ref="frag_001",
    )
    record = normalize_rfs_failure(audit, packet)

    with get_session() as session:
        save_failure_record(
            session,
            record,
            audit,
            condition_hash=packet.condition_hash,
            ruleset_fingerprint=packet.ruleset_fingerprint,
            request_id="req-failure",
        )

    with get_session() as session:
        failures = list_recent_failures(session, limit=20)
        assert len(failures) == 1
        assert failures[0].failure_signature == "object_rotation_error"
        assert failures[0].failure_category == "topology_dof_violation"
        assert failures[0].bad_prompt_fragment == "她轻轻推开了推拉窗"
