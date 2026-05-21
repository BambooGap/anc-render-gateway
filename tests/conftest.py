from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def temporary_database_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANC_GATEWAY_DB_URL", f"sqlite:///{tmp_path / 'anc_gateway_test.db'}")
