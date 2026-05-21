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
