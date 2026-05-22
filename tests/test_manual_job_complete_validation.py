"""Tests for CompleteManualJobRequest validation."""

import pytest
from pydantic import ValidationError

from anc_gateway.manual.schemas import CompleteManualJobRequest


def test_complete_manual_job_accepts_valid_file_uri() -> None:
    request = CompleteManualJobRequest(result_video_uri="file:///tmp/manual_video.mp4")
    assert request.result_video_uri == "file:///tmp/manual_video.mp4"


def test_complete_manual_job_accepts_valid_mock_uri() -> None:
    request = CompleteManualJobRequest(result_video_uri="mock://renders/example.mp4")
    assert request.result_video_uri == "mock://renders/example.mp4"


def test_complete_manual_job_accepts_valid_https_uri() -> None:
    request = CompleteManualJobRequest(result_video_uri="https://example.com/video.mp4")
    assert request.result_video_uri == "https://example.com/video.mp4"


def test_complete_manual_job_strips_whitespace() -> None:
    request = CompleteManualJobRequest(result_video_uri="  file:///tmp/video.mp4  ")
    assert request.result_video_uri == "file:///tmp/video.mp4"


def test_complete_manual_job_rejects_empty_string() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CompleteManualJobRequest(result_video_uri="")
    assert "result_video_uri" in str(exc_info.value)


def test_complete_manual_job_rejects_whitespace_only() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CompleteManualJobRequest(result_video_uri="   ")
    assert "result_video_uri" in str(exc_info.value)


def test_complete_manual_job_rejects_tab_whitespace() -> None:
    with pytest.raises(ValidationError) as exc_info:
        CompleteManualJobRequest(result_video_uri="\t\n")
    assert "result_video_uri" in str(exc_info.value)
