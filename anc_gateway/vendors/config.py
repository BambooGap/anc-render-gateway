from __future__ import annotations

import os

from pydantic import BaseModel

from anc_gateway.vendors.errors import VendorConfigurationError


class VendorHTTPConfig(BaseModel):
    vendor: str
    model: str
    base_url: str
    api_key_env: str
    timeout_seconds: float = 60.0
    poll_interval_seconds: float = 5.0
    max_poll_attempts: int = 60


def load_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise VendorConfigurationError(f"Missing API key environment variable: {env_name}")
    return api_key
