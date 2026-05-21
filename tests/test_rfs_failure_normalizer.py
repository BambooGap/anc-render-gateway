from anc_gateway.rfs.failure_taxonomy import normalize_failure_signature


def test_failure_signature_window_flip() -> None:
    normalized = normalize_failure_signature("window_flipping_bug")
    assert normalized.category == "topology_dof_violation"
    assert normalized.signature == "object_rotation_error"


def test_failure_signature_contact() -> None:
    normalized = normalize_failure_signature("hand_not_touching_panel")
    assert normalized.category == "contact_failure"
    assert normalized.signature == "hand_panel_misalignment"
