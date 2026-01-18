import asyncio
from textwrap import dedent

from loguru import logger
from pydantic import BaseModel

from ..core.prompting import PromptSpec
from ..lazy import lazy_run
from .instructions import BASE_INSTRUCTIONS
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
    highlights: list[str]
    causal_relationships: list[CausalRelationship]
    conclusion: str

    def __str__(self) -> str:
        lines = []

        lines.append(f"{self.title}")
        lines.append(f"📝 摘要\n{self.abstract}")
        lines.append(f"🔍 介紹\n{self.introduction}")
        lines.append(f"⚙️ 方法\n{self.methodology}")

        if self.highlights:
            lines.append("\n".join(["✨ 重點"] + [f"- {highlight}" for highlight in self.highlights]))

        if self.causal_relationships:
            lines.append(
                "\n".join(["🔄 因果關係"] + [f"- {relationship}" for relationship in self.causal_relationships])
            )

        lines.append(f"🎯 結論\n{self.conclusion}")

        return "\n\n".join(lines)


EXTRACT_NOTES_PROMPT = PromptSpec(
    id="extract_notes",
    version=1,
    name="extract_notes",
    input_template="""
As a research assistant, you will take to analyze the provided text and organize it
into a structured research report in the specified language ({lang}).

Guidelines:
- Extract only factual information present in the text; do not include speculative or interpretive content.
- Organize the report into the specified sections, maintaining the exact sequence below.
- For unknown, missing, or uncertain information, use empty strings or lists; do not fabricate content.
- If any input data is missing or malformed, represent it as an empty string or list and proceed with
  available information.
- If required variables such as {lang} or {text} are undefined, use empty strings as placeholders.

After structuring the report, review your output to ensure all guidelines and output format requirements are followed,
including correct handling of missing or malformed data.

Create a research report with the following sections, in strict order:
1. Title: A descriptive heading reflecting the main subject
2. Abstract: Concise summary of key points
3. Introduction: Explanation of context and purpose
4. Methodology: Description of approaches or methods used
5. Key Highlights: Bullet-point findings
6. Causal Relationships: List each in 'cause -> effect' format
7. Conclusion: Summary of implications and importance

Translate ALL content into **{lang}**.
ALL output MUST be written in **{lang}**.

Input text:
```
{text}
```
""",
    output_type=ResearchReport,
)

CHUNK_NOTES_PROMPT = PromptSpec(
    id="create_notes_from_chunk",
    version=1,
    name="create_notes_from_chunk",
    input_template="""
You are a researcher skilled in creating concise, well-organized study notes.

Set reasoning_effort = minimal; use only as much detail as needed for accuracy and clarity.

Your objective is to produce study notes based on the text provided, following a clear,
step-by-step format while ensuring accuracy and neutrality.

Guidelines:
- Carefully read the supplied text.
- Organize the information into logically structured study notes.
- Use neutral, factual language only.
- Do not add, infer, or fabricate any information; include only what is explicitly stated in the text.
- Ensure notes are concise yet comprehensive.
- Present information in a step-by-step format.

Text:
```
{text}
```
""",
)


async def extract_notes(text: str, target_lang: str = "台灣正體中文") -> ResearchReport:
    """Extract structured research notes from text.

    Args:
        text: The text content to extract notes from
        target_lang: Target language for the notes (default: "台灣正體中文")

    Returns:
        ResearchReport: Structured research report with sections
    """
    report = await lazy_run(
        input=dedent(EXTRACT_NOTES_PROMPT.render_input(text=text, lang=target_lang)),
        instructions=EXTRACT_NOTES_PROMPT.render_instructions(BASE_INSTRUCTIONS, lang=target_lang),
        name=EXTRACT_NOTES_PROMPT.name or "lazy_run",
        output_type=ResearchReport,
    )

    logger.info("Formatted report: {report}", report=report)
    return report


async def create_notes_from_chunk(text: str) -> str:
    """Create concise study notes from a text chunk.

    Args:
        text: The text chunk to process

    Returns:
        str: Formatted study notes
    """
    prompt = dedent(CHUNK_NOTES_PROMPT.render_input(text=text))
    result = await lazy_run(
        prompt,
        instructions=CHUNK_NOTES_PROMPT.render_instructions(BASE_INSTRUCTIONS),
        name=CHUNK_NOTES_PROMPT.name or "lazy_run",
    )
    return result


async def create_notes(text: str) -> ResearchReport:
    """Create structured research notes from text, handling long texts by chunking.

    For long texts that exceed the chunk limit, the text is split into chunks,
    each chunk is processed into notes, and then the combined notes are formatted.

    Args:
        text: The text content to create notes from

    Returns:
        ResearchReport: Structured research report with sections
    """
    chunks = chunk_on_delimiter(text)

    if len(chunks) == 1:
        return await extract_notes(text)

    chunk_notes = await asyncio.gather(*[create_notes_from_chunk(chunk) for chunk in chunks])
    return await extract_notes("\n".join(chunk_notes))
