import asyncio
from textwrap import dedent
from typing import cast

from loguru import logger
from pydantic import BaseModel

from ..lazy import parse
from .notes import create_notes_from_chunk
from .utils import chunk_on_delimiter


class FormattedContent(BaseModel):
    title: str
    content: str

    def __str__(self) -> str:
        return self.content


async def _format(text: str, lang: str = "台灣中文") -> FormattedContent:
    prompt = f"""
    Extract and organize information from the input text, then translate it to {lang}.
    Do not fabricate any information.

    Please return:
    1. A clear, concise title in {lang}
    2. Well-structured Markdown content in {lang} that:
       - Uses appropriate heading levels
       - Includes lists or tables when helpful
       - Maintains the core meaning and important details from the original text

    Input text:
    ```
    {text}
    ```
    """.strip()  # noqa: E501
    response = cast(
        FormattedContent,
        await parse(
            dedent(prompt),
            output_type=FormattedContent,
        ),
    )

    logger.info("Formatted response: {response}", response=response)
    return response


async def format(text: str, lang: str = "台灣中文") -> FormattedContent:
    chunks = chunk_on_delimiter(text)

    if len(chunks) == 1:
        return await _format(text)

    results = await asyncio.gather(*[create_notes_from_chunk(chunk) for chunk in chunks])
    return await _format("\n".join(results))
