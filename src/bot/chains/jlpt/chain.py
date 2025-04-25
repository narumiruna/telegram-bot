from __future__ import annotations

from ...lazy import send
from .prompts import JLPT_V3


async def learn_japanese(text: str) -> str:
    return str(await send(text, instructions=JLPT_V3))
