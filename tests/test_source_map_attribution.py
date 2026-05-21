import pytest

from anc_gateway.core.compiler import compile_render_packet
from anc_gateway.core.schemas import RFSAuditResult, RenderContract, StateT
from anc_gateway.core.source_map import SourceMapAttributionError
from anc_gateway.rfs.failure_normalizer import normalize_rfs_failure


def test_source_map_attribution_unknown_ref_raises() -> None:
    packet = compile_render_packet(
        StateT(id="state_001", shot_id="shot_001"),
        RenderContract(shot_id="shot_001"),
        "她轻轻推开了推拉窗，风吹进房间。",
    )

    with pytest.raises(SourceMapAttributionError):
        normalize_rfs_failure(
            RFSAuditResult(
                ok=False,
                raw_signature="window_flipping_bug",
                bad_prompt_fragment_ref="frag_999",
            ),
            packet,
        )
