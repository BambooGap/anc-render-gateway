"""Tests for casebase deduplication logic."""

from __future__ import annotations

from fastapi.testclient import TestClient

from anc_gateway.api.app import app
from anc_gateway.casebase.recommendations import _dedup_candidates
from anc_gateway.casebase.schemas import RecommendedPatch

client = TestClient(app)


def _make_patch(
    patch_prompt: str,
    ranking_score: float,
    case_id: str = "case_001",
    failure_signature: str = "object_rotation_error",
) -> RecommendedPatch:
    return RecommendedPatch(
        failure_signature=failure_signature,
        patch_prompt=patch_prompt,
        ranking_score=ranking_score,
        case_id=case_id,
        confidence=0.9,
    )


def test_dedup_removes_duplicate_patch_prompts() -> None:
    """Duplicate patch_prompt entries should be merged."""
    candidates = [
        _make_patch("保持阀门中心轴旋转稳定", 0.8, "case_001"),
        _make_patch("保持阀门中心轴旋转稳定", 0.6, "case_002"),
        _make_patch("推拉窗沿轨道水平滑动", 0.7, "case_003"),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 2


def test_dedup_keeps_highest_score() -> None:
    """Dedup should keep the entry with the highest ranking_score."""
    candidates = [
        _make_patch("保持阀门中心轴旋转稳定", 0.6, "case_002"),
        _make_patch("保持阀门中心轴旋转稳定", 0.9, "case_001"),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 1
    assert result[0].ranking_score == 0.9
    assert result[0].case_id == "case_001"


def test_dedup_increments_duplicate_count() -> None:
    """Dedup should increment duplicate_count for merged entries."""
    candidates = [
        _make_patch("保持阀门中心轴旋转稳定", 0.8, "case_001"),
        _make_patch("保持阀门中心轴旋转稳定", 0.6, "case_002"),
        _make_patch("保持阀门中心轴旋转稳定", 0.5, "case_003"),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 1
    assert result[0].duplicate_count == 3


def test_dedup_counts_distinct_source_cases() -> None:
    """Dedup should count distinct source cases."""
    candidates = [
        _make_patch("保持阀门中心轴旋转稳定", 0.8, "case_001"),
        _make_patch("保持阀门中心轴旋转稳定", 0.6, "case_002"),
        _make_patch("保持阀门中心轴旋转稳定", 0.5, "case_001"),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 1
    assert result[0].source_case_count == 2


def test_dedup_empty_list() -> None:
    """Dedup on empty list returns empty list."""
    assert _dedup_candidates([]) == []


def test_dedup_no_duplicates() -> None:
    """No duplicates means all entries preserved."""
    candidates = [
        _make_patch("patch_a", 0.8),
        _make_patch("patch_b", 0.7),
        _make_patch("patch_c", 0.6),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 3


def test_dedup_none_patch_prompt() -> None:
    """None patch_prompt should be treated as empty string for dedup."""
    candidates = [
        _make_patch(None, 0.8),  # type: ignore[arg-type]
        _make_patch(None, 0.6),  # type: ignore[arg-type]
        _make_patch("valid_patch", 0.7),
    ]
    result = _dedup_candidates(candidates)
    assert len(result) == 2
