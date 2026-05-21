from __future__ import annotations

from pydantic import BaseModel, Field


class VendorCapability(BaseModel):
    vendor: str
    model: str
    text_to_video: bool
    image_to_video: bool
    first_frame: bool
    last_frame: bool
    first_last_interpolation: bool
    inpainting_mask: bool
    negative_prompt: bool
    seed: bool
    motion_strength: bool
    max_prompt_chars: int | None
    supported_aspect_ratios: list[str] = Field(default_factory=list)


MOCK_VENDOR_CAPABILITY = VendorCapability(
    vendor="mock",
    model="mock-video-v1",
    text_to_video=True,
    image_to_video=True,
    first_frame=True,
    last_frame=False,
    first_last_interpolation=False,
    inpainting_mask=False,
    negative_prompt=False,
    seed=False,
    motion_strength=False,
    max_prompt_chars=None,
    supported_aspect_ratios=["16:9", "9:16", "1:1"],
)


def get_vendor_capability(vendor: str) -> VendorCapability:
    if vendor == "mock":
        return MOCK_VENDOR_CAPABILITY
    raise ValueError(f"Unknown vendor capability: {vendor}")
