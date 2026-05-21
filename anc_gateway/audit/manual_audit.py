from __future__ import annotations

from anc_gateway.audit.schemas import ManualAuditCreateRequest
from anc_gateway.core.schemas import RFSAuditResult

DEFAULT_MANUAL_RFS_SCORES = {
    "overall": 0.5,
    "manual_review": 1.0,
}


def build_rfs_audit_from_manual_request(request: ManualAuditCreateRequest) -> RFSAuditResult:
    raw_signature = request.failure_type
    details = {
        "source": "manual_rfs_audit",
        "observed": request.notes,
        "rfs_scores": request.rfs_scores or DEFAULT_MANUAL_RFS_SCORES,
        "manual_job_id": request.manual_job_id,
        "render_job_id": request.render_job_id,
        "condition_hash": request.condition_hash,
    }
    return RFSAuditResult(
        ok=False,
        raw_signature=raw_signature,
        bad_prompt_fragment_ref=request.bad_prompt_fragment_ref,
        details=details,
    )
