from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_case_export_markdown_contains_obsidian_ready_sections() -> None:
    case = client.post(
        "/cases",
        json={"title": "Obsidian 复盘", "raw_prompt": "她推开推拉窗。"},
    ).json()
    attempt = client.post(
        f"/cases/{case['case_id']}/attempts",
        json={
            "raw_prompt": "她推开推拉窗。",
            "compiled_prompt": "她右手推开推拉窗。",
            "condition_hash": "hash_export",
        },
    ).json()
    client.post(
        f"/attempts/{attempt['attempt_id']}/manual-audit",
        json={"manual_audit_id": "audit_export", "failure_record_id": "failure_export"},
    )
    client.post(
        f"/attempts/{attempt['attempt_id']}/patch",
        json={
            "patch_packet": {"patch_prompt": "窗扇只沿上下轨道水平滑动。"},
            "patch_record_id": "patch_export",
        },
    )

    response = client.get(f"/cases/{case['case_id']}/export.md")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    markdown = response.text
    assert "# Obsidian 复盘" in markdown
    assert "## Base Prompt" in markdown
    assert "### Attempt 1" in markdown
    assert "- Raw Prompt: 她推开推拉窗。" in markdown
    assert "- Patch Record ID: patch_export" in markdown
    assert "## Lessons Learned" in markdown
