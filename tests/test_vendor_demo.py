from typing import Any

from anc_gateway.cli import main


def test_vendor_demo_runs(capsys: Any) -> None:
    main(["vendor-demo"])

    output = capsys.readouterr().out
    assert "vendor_render_job" in output
    assert "mock_external_" in output
    assert "mock://renders/" in output
    assert "SUCCEEDED" in output
    assert "object_rotation_error" in output
