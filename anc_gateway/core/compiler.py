from __future__ import annotations

import re

from anc_gateway.core.hashes import compute_condition_hash
from anc_gateway.core.schemas import CompiledRenderPacket, RenderContract, StateT
from anc_gateway.core.source_map import SourceMapRegistry
from anc_gateway.linter.positive_lock_rewriter import rewrite_positive_locks
from anc_gateway.linter.token_budget import compress_text_to_budget
from anc_gateway.linter.topology_rules import apply_topology_rules


def compile_render_packet(
    state: StateT,
    render_contract: RenderContract,
    raw_prompt: str,
) -> CompiledRenderPacket:
    registry = SourceMapRegistry()
    compiled_fragments: list[str] = []

    for raw_fragment in _split_prompt(raw_prompt):
        fragment_ref = registry.register(raw_fragment)

        topology_result = apply_topology_rules(raw_fragment, fragment_ref, state)
        positive_result = rewrite_positive_locks(topology_result.text, fragment_ref)

        rules_applied = topology_result.rules_applied + [
            rule
            for rule in positive_result.rules_applied
            if rule not in topology_result.rules_applied
        ]
        compiled_text = compress_text_to_budget(
            positive_result.text, render_contract.max_prompt_chars
        )
        registry.update(fragment_ref, compiled_text, rules_applied)
        compiled_fragments.append(compiled_text)

    compiled_prompt = _join_fragments(compiled_fragments)
    condition_hash = compute_condition_hash(
        compiled_prompt=compiled_prompt,
        state=state,
        render_contract=render_contract,
    )
    return CompiledRenderPacket(
        state_id=state.id,
        shot_id=render_contract.shot_id,
        compiled_prompt=compiled_prompt,
        source_map=registry.to_source_map(),
        condition_hash=condition_hash,
        ruleset_fingerprint=render_contract.ruleset_fingerprint,
        compiler_version=render_contract.compiler_version,
    )


def _split_prompt(raw_prompt: str) -> list[str]:
    fragments = [part.strip() for part in re.split(r"[，。；;\n]+", raw_prompt)]
    return [part for part in fragments if part]


def _join_fragments(fragments: list[str]) -> str:
    return "，".join(fragment.strip("，。 ") for fragment in fragments if fragment).strip()
