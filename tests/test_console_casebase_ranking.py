"""Tests for console UI casebase ranking features."""

from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "anc_gateway" / "web" / "static"


def test_index_html_has_object_type_input() -> None:
    """Console should have object_type input in recommend section."""
    html = (STATIC_DIR / "index.html").read_text()
    assert 'id="recommendObjectType"' in html


def test_index_html_has_motion_model_input() -> None:
    """Console should have motion_model input in recommend section."""
    html = (STATIC_DIR / "index.html").read_text()
    assert 'id="recommendMotionModel"' in html


def test_app_js_sends_object_type() -> None:
    """app.js recommendPatches should send object_type in payload."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "object_type" in js


def test_app_js_sends_motion_model() -> None:
    """app.js recommendPatches should send motion_model in payload."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "motion_model" in js


def test_app_js_render_recommendations() -> None:
    """app.js should have renderRecommendations function."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "renderRecommendations" in js


def test_app_js_shows_ranking_score() -> None:
    """app.js renderRecommendations should display ranking_score."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "ranking_score" in js


def test_app_js_shows_reason() -> None:
    """app.js renderRecommendations should display reason."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "reason" in js


def test_app_js_shows_matched_by() -> None:
    """app.js renderRecommendations should display matched_by."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "matched_by" in js


def test_app_js_shows_duplicate_count() -> None:
    """app.js renderRecommendations should display duplicate_count."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "duplicate_count" in js


def test_app_js_shows_source_case_count() -> None:
    """app.js renderRecommendations should display source_case_count."""
    js = (STATIC_DIR / "app.js").read_text()
    assert "source_case_count" in js
