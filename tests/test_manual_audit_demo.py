from typing import Any

from anc_gateway.cli import main


def test_manual_audit_demo_runs(capsys: Any) -> None:
    main(["manual-audit-demo"])

    output = capsys.readouterr().out
    assert "manual_job" in output
    assert "manual_audit" in output
    assert "window_flipping_bug" in output
    assert "object_rotation_error" in output
    assert "patch_packet" in output
