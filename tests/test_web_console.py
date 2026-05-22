from fastapi.testclient import TestClient

from anc_gateway.api.app import app


client = TestClient(app)


def test_console_serves_html_and_static_assets() -> None:
    html_response = client.get("/console")
    app_js_response = client.get("/console/static/app.js")
    styles_response = client.get("/console/static/styles.css")

    assert html_response.status_code == 200
    assert app_js_response.status_code == 200
    assert styles_response.status_code == 200
    html = html_response.text
    assert "Compile" in html
    assert "Manual Job" in html
    assert "Manual Audit" in html
    assert "Recover" in html
    assert "Workspace" in html
    assert "Source Map Fragments" in html
    assert "Copy Patch Prompt" in html

    styles = styles_response.text
    assert "pre-wrap" in styles

    app_js = app_js_response.text
    assert "fragmentQuickList" in app_js
    assert "renderFragmentQuickList" in app_js
    assert "copyPatchPrompt" in app_js
    assert "createNextAttemptFromPatch" in app_js
