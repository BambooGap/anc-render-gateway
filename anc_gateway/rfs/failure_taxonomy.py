from __future__ import annotations

from pydantic import BaseModel


class NormalizedFailureSignature(BaseModel):
    category: str
    signature: str


_SIGNATURES: dict[str, NormalizedFailureSignature] = {
    "window_flipping_bug": NormalizedFailureSignature(
        category="topology_dof_violation", signature="object_rotation_error"
    ),
    "window_flip": NormalizedFailureSignature(
        category="topology_dof_violation", signature="object_rotation_error"
    ),
    "hinged_window_wrongly_generated": NormalizedFailureSignature(
        category="topology_dof_violation", signature="object_rotation_error"
    ),
    "window_rotated_outward": NormalizedFailureSignature(
        category="topology_dof_violation", signature="object_rotation_error"
    ),
    "hand_not_touching_panel": NormalizedFailureSignature(
        category="contact_failure", signature="hand_panel_misalignment"
    ),
}


def normalize_failure_signature(raw_signature: str) -> NormalizedFailureSignature:
    normalized = raw_signature.strip().lower()
    return _SIGNATURES.get(
        normalized,
        NormalizedFailureSignature(category="unknown_failure", signature=normalized),
    )
