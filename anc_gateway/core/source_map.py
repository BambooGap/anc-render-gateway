from __future__ import annotations

from anc_gateway.core.schemas import PromptFragment, PromptSourceMap


class SourceMapAttributionError(LookupError):
    """Raised when an RFS failure cannot be attributed to a source fragment."""


class SourceMapRegistry:
    def __init__(self) -> None:
        self._fragments: dict[str, PromptFragment] = {}
        self._counter = 0

    def register(self, original_text: str) -> str:
        self._counter += 1
        fragment_ref = f"frag_{self._counter:03d}"
        self._fragments[fragment_ref] = PromptFragment(
            fragment_ref=fragment_ref,
            original_text=original_text,
            compiled_text=original_text,
        )
        return fragment_ref

    def update(
        self,
        fragment_ref: str,
        compiled_text: str,
        rules_applied: list[str] | None = None,
    ) -> None:
        fragment = self.get(fragment_ref)
        merged_rules = list(fragment.rules_applied)
        for rule_id in rules_applied or []:
            if rule_id not in merged_rules:
                merged_rules.append(rule_id)
        self._fragments[fragment_ref] = fragment.model_copy(
            update={"compiled_text": compiled_text, "rules_applied": merged_rules}
        )

    def get(self, fragment_ref: str) -> PromptFragment:
        try:
            return self._fragments[fragment_ref]
        except KeyError as exc:
            raise SourceMapAttributionError(
                f"Unknown source map fragment: {fragment_ref}"
            ) from exc

    def to_source_map(self) -> PromptSourceMap:
        return PromptSourceMap(fragments=dict(self._fragments))
