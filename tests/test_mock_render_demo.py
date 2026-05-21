from anc_gateway.cli import main


def test_mock_render_demo_runs(capsys) -> None:  # type: ignore[no-untyped-def]
    main(["mock-render-demo"])

    output = capsys.readouterr().out
    assert "compiled_render_packet" in output
    assert "render_job" in output
    assert "SUCCEEDED" in output
    assert "mock://renders/" in output
    assert "object_rotation_error" in output
