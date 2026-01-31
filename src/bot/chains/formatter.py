import asyncio
from textwrap import dedent

from agents import trace
from loguru import logger
from pydantic import BaseModel

from bot.core.prompting import PromptSpec
from bot.lazy import lazy_run
from bot.presentation import MessageResponse

from .instructions import BASE_INSTRUCTIONS
from .notes import create_notes_from_chunk
from .utils import chunk_on_delimiter


class Article(BaseModel):
    title: str
    content: str

    def __str__(self) -> str:
        return "\n\n".join(
            [
                f"📝 {self.title}",
                self.content,
            ]
        )

    def to_message_response(self) -> MessageResponse:
        """Convert article to a MessageResponse for sending.

        Returns:
            MessageResponse ready to be sent to Telegram
        """
        return MessageResponse(
            content=str(self),
            title=self.title,
            parse_mode=None,  # Plain text
        )


FORMAT_PROMPT = PromptSpec(
    id="format",
    version=1,
    name="format",
    input_template="""
Extract and organize information from the input text, then translate it into {lang}.
Do not invent or add information.

Create an overall article title that summarizes the entire input in {lang}; avoid generic placeholders like "Article" or "Summary".

Use clear, accessible language that is easy for the general public to understand. When the input includes legal,
technical, or other complex documents, rephrase the content in plain language appropriate for ordinary readers.

Respond in plain text only. Do not use Markdown, HTML, or any other markup syntax.

For each section:
- Begin with a relevant emoji (matching the section's theme) and a concise section title in {lang} on the first line,
  separated by a single space.
- On the next line, present the well-organized content in {lang}, ensuring the main message and essential details
  are preserved.
- Use multiple sections if the input covers distinct topics, major points, or separate thematic paragraphs.

If the input text is empty, respond with:
[No content provided]

If a section already includes an emoji or title, update the title as needed and select a new emoji that fits
the reorganized content.

If section boundaries are unclear, treat each major paragraph, bullet point, or heading as a distinct section.
When the structure is confusing, do your best to organize the information into clear, separate sections.

After completing all sections, review the output to ensure all requirements are met and revise minimally if needed.

Translate ALL content into **{lang}**.
ALL output MUST be written in **{lang}**.

Input text:
```
{text}
```
""",  # noqa: E501
)


async def _format(text: str, target_lang: str = "台灣正體中文") -> Article:
    """Format text into a structured article with sections.

    Args:
        text: The text content to format
        target_lang: Target language for the formatted output (default: "台灣正體中文")

    Returns:
        Article: Structured article with title and sections
    """
    prompt = FORMAT_PROMPT.render_input(text=text, lang=target_lang)

    with trace("format"):
        article = await lazy_run(
            dedent(prompt),
            instructions=FORMAT_PROMPT.render_instructions(BASE_INSTRUCTIONS, lang=target_lang),
            name=FORMAT_PROMPT.name or "lazy_run",
            output_type=Article,
        )

    logger.info("Formatted article: {article}", article=article)
    return article


async def format(text: str, target_lang: str = "台灣正體中文") -> Article:
    """Format text into a structured article, handling long texts by chunking.

    For long texts that exceed the chunk limit, the text is split into chunks,
    each chunk is processed into notes, and then the combined notes are formatted.

    Args:
        text: The text content to format
        target_lang: Target language for the formatted output (default: "台灣正體中文")

    Returns:
        Article: Structured article with title and sections
    """
    chunks = chunk_on_delimiter(text)

    if len(chunks) == 1:
        return await _format(text, target_lang=target_lang)

    chunk_notes = await asyncio.gather(*[create_notes_from_chunk(chunk) for chunk in chunks])
    return await _format("\n".join(chunk_notes), target_lang=target_lang)
