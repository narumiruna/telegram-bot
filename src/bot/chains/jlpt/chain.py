from __future__ import annotations

from ...lazy import lazy_run
from .prompts import JLPT_V3


async def learn_japanese(text: str) -> str:
    return str(await lazy_run(text, instructions=JLPT_V3))
