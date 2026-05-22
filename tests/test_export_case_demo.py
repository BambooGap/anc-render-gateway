import subprocess
import sys


def test_export_case_demo_runs_and_prints_markdown() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "anc_gateway.cli", "export-case-demo"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# export-case-demo" in result.stdout
    assert "## Base Prompt" in result.stdout
    assert "### Attempt 1" in result.stdout
    assert "- Patch Record ID:" in result.stdout
