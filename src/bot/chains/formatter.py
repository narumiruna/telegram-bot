import asyncio
from textwrap import dedent
from typing import cast

from loguru import logger
from pydantic import BaseModel

from ..lazy import parse
from .notes import create_notes_from_chunk
from .utils import chunk_on_delimiter


class Section(BaseModel):
    title: str
    content: str

    def __str__(self) -> str:
        return f"{self.title}\n{self.content}"


class Article(BaseModel):
    title: str
    sections: list[Section]

    def __str__(self) -> str:
        lines = [f"📝 {self.title}"]
        lines += [str(section) for section in self.sections]
        return "\n\n".join(lines)


async def _format(text: str, lang: str = "台灣中文") -> Article:
    prompt = f"""
    Extract and organize information from the input text, then translate it to {lang}.
    Do not fabricate any information.

    Please use plain text only (no Markdown or any formatting syntax).

    For each section:
    - Start with an appropriate emoji and a concise title in {lang} on one line.
    - The next line should be the well-organized content in {lang}, preserving the core meaning and important details.
    - Use multiple sections if there are distinct topics or points.

    Input text:
    ```
    {text}
    ```
    """.strip()  # noqa: E501
    response = cast(
        Article,
        await parse(
            dedent(prompt),
            output_type=Article,
        ),
    )

    logger.info("Formatted response: {response}", response=response)
    return response


async def format(text: str, lang: str = "台灣中文") -> Article:
    chunks = chunk_on_delimiter(text)

    if len(chunks) == 1:
        return await _format(text)

    results = await asyncio.gather(*[create_notes_from_chunk(chunk) for chunk in chunks])
    return await _format("\n".join(results))
