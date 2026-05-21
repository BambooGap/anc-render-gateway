from __future__ import annotations

from typing import Any

from anc_gateway.core.hashes import sha256_text, stable_json_dumps


def compute_render_hash(
    *,
    condition_hash: str,
    vendor: str,
    model: str,
    visual_anchor_uri: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    payload = {
        "condition_hash": condition_hash,
        "vendor": vendor,
        "model": model,
        "visual_anchor_uri": visual_anchor_uri,
        "metadata": metadata or {},
    }
    return sha256_text(stable_json_dumps(payload))
