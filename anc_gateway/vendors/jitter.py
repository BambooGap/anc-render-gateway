from __future__ import annotations

from enum import StrEnum


class JitterStrategy(StrEnum):
    NONE = "NONE"
    VENDOR_PARAM = "VENDOR_PARAM"
    SOFT_CONSTRAINT_TEXT = "SOFT_CONSTRAINT_TEXT"
    ANCHOR_FRAME = "ANCHOR_FRAME"


_SOFT_CONSTRAINT_VARIANTS = [
    "漂浮尘埃缓慢穿过冷白光束",
    "冷白灯光中可见稀薄的微小颗粒轻微漂移",
    "背景中的冷白应急灯轻微闪烁",
    "室内应急照明产生细微光强起伏",
]


def apply_soft_constraint_jitter(prompt: str, attempt: int) -> str:
    if attempt <= 0:
        return prompt

    replacement = _SOFT_CONSTRAINT_VARIANTS[attempt % len(_SOFT_CONSTRAINT_VARIANTS)]
    for candidate in _SOFT_CONSTRAINT_VARIANTS:
        if candidate in prompt:
            return prompt.replace(candidate, replacement)

    return f"{prompt}，{replacement}"
