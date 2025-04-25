import asyncio
from textwrap import dedent
from typing import cast

from loguru import logger
from pydantic import BaseModel

from ..lazy import parse
from ..lazy import send
from .utils import chunk_on_delimiter


class CausalRelationship(BaseModel):
    cause: str
    effect: str

    def __str__(self) -> str:
        return f"{self.cause} -> {self.effect}"


class ResearchReport(BaseModel):
    title: str
    abstract: str
    introduction: str
    methodology: str
    hightlights: list[str]
    causal_relationships: list[CausalRelationship]
    conclusion: str

    def __str__(self) -> str:
        lines = []

        lines.append(f"{self.title}")
        lines.append(f"📝 摘要\n{self.abstract}")
        lines.append(f"🔍 介紹\n{self.introduction}")
        lines.append(f"⚙️ 方法\n{self.methodology}")

        if self.hightlights:
            lines.append("\n".join(["✨ 重點"] + [f"- {highlight}" for highlight in self.hightlights]))

        if self.causal_relationships:
            lines.append(
                "\n".join(["🔄 因果關係"] + [f"- {relationship}" for relationship in self.causal_relationships])
            )

        lines.append(f"🎯 結論\n{self.conclusion}")

        return "\n\n".join(lines)


async def extract_notes(text: str, lang: str = "台灣中文") -> ResearchReport:
    prompt = f"""
    As a research assistant, analyze the provided text and organize it into a structured research report in {lang}.

    Guidelines:
    - Extract only factual information present in the text
    - Do not add speculative or interpretive content
    - Format with clear sections and logical flow
    - If information is unknown or uncertain, use empty strings or empty lists instead of fabricating facts

    Please create a research report with:
    1. A descriptive title that captures the main subject
    2. A brief abstract summarizing key points
    3. An introduction explaining the context and purpose
    4. A methodology section describing approaches or methods used
    5. Key highlights or findings (as bullet points)
    6. Causal relationships identified in the text (cause -> effect format)
    7. A conclusion summarizing implications and importance

    Input text:
    ```
    {text}
    ```
    """.strip()  # noqa: E501
    response = cast(
        ResearchReport,
        await parse(
            input=dedent(prompt),
            output_type=ResearchReport,
        ),
    )

    logger.info("Formatted response: {response}", response=response)
    return response


async def create_notes_from_chunk(text: str) -> str:
    prompt = dedent(f"""
    You are a researcher adept at creating concise, well-structured study notes. Your goal is to create a study notes based on the text below in a clear, step-by-step manner while maintaining accuracy and neutrality. Please adhere to the following guidelines:

    - Thoroughly read the text provided.
    - Generate study notes that organize the information in a logical structure.
    - Use neutral, factual language.
    - Do not add, infer, or fabricate any details—only use what the text explicitly states.
    - Keep the notes concise yet comprehensive.
    - Maintain a clear, step-by-step approach throughout the notes.

    Text:
    ```
    {text}
    ```
    """).strip()  # noqa
    result = await send(prompt)
    return result


async def create_notes(text: str) -> ResearchReport:
    chunks = chunk_on_delimiter(text)

    if len(chunks) == 1:
        return await extract_notes(text)

    results = await asyncio.gather(*[create_notes_from_chunk(chunk) for chunk in chunks])
    return await extract_notes("\n".join(results))
