import pytest

from anc_gateway.audit.manual_audit import build_rfs_audit_from_manual_request
from anc_gateway.audit.schemas import ManualAuditCreateRequest


def test_build_manual_rfs_audit_window_flip() -> None:
    request = ManualAuditCreateRequest(
        bad_prompt_fragment_ref="frag_001",
        failure_type="window_flipping_bug",
    )

    audit = build_rfs_audit_from_manual_request(request)

    assert audit.ok is False
    assert audit.raw_signature == "window_flipping_bug"
    assert audit.bad_prompt_fragment_ref == "frag_001"
    assert audit.details["rfs_scores"]["overall"] == 0.5


def test_build_manual_rfs_audit_custom_requires_notes() -> None:
    with pytest.raises(ValueError):
        ManualAuditCreateRequest(
            bad_prompt_fragment_ref="frag_001",
            failure_type="custom",
        )


def test_build_manual_rfs_audit_custom_includes_observed_notes() -> None:
    request = ManualAuditCreateRequest(
        bad_prompt_fragment_ref="frag_001",
        failure_type="custom",
        notes="模型忽略了人物左侧的参考图。",
        rfs_scores={"overall": 0.2},
    )

    audit = build_rfs_audit_from_manual_request(request)

    assert audit.raw_signature == "custom"
    assert audit.details["observed"] == "模型忽略了人物左侧的参考图。"
    assert audit.details["rfs_scores"] == {"overall": 0.2}
