from typing import Any

from anc_gateway.cli import main


def test_manual_demo_runs(capsys: Any) -> None:
    main(["manual-demo"])

    output = capsys.readouterr().out
    assert "manual_job" in output
    assert "copy_instructions" in output
    assert "file:///tmp/mock_video.mp4" in output
    assert "object_rotation_error" in output
    assert "patch_packet" in output
