from __future__ import annotations

from anc_gateway.core.schemas import CompiledRenderPacket, PromptFragment
from anc_gateway.core.source_map import SourceMapAttributionError


def attribute_failure_fragment(
    packet: CompiledRenderPacket, bad_prompt_fragment_ref: str | None
) -> PromptFragment:
    if bad_prompt_fragment_ref:
        try:
            return packet.source_map.fragments[bad_prompt_fragment_ref]
        except KeyError as exc:
            raise SourceMapAttributionError(
                f"Unknown source map fragment: {bad_prompt_fragment_ref}"
            ) from exc

    if len(packet.source_map.fragments) == 1:
        return next(iter(packet.source_map.fragments.values()))

    for fragment in packet.source_map.fragments.values():
        if any(rule in fragment.rules_applied for rule in ("ANC-LINT-001", "ANC-LINT-002")):
            return fragment

    raise SourceMapAttributionError("RFS failure did not include a fragment reference")
