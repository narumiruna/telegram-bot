import asyncio
import logging
from textwrap import dedent

from agents import trace
from pydantic import BaseModel

from bot.core.presentation import MessageResponse
from bot.core.prompting import PromptSpec
from bot.lazy import lazy_run

from .instructions import BASE_INSTRUCTIONS
from .notes import create_notes_from_chunk
from .utils import chunk_on_delimiter

logger = logging.getLogger(__name__)


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
Extract, reorganize, and translate the input text into {lang}.
Do not fabricate, infer, or add any information beyond the input.

Generate a clear, specific article title in {lang} that accurately summarizes the entire input.
Do not use generic titles such as “Article” or “Summary”.

Rewrite the content in plain, accessible language suitable for the general public.
If the input is legal, technical, or otherwise complex, simplify the wording while preserving all essential facts and meaning.

Output rules:

Respond in plain text only.
Do not use Markdown, HTML, or any markup syntax.

Structure rules:

Organize the content into multiple sections when there are distinct topics, themes, paragraphs, headings, or bullet points.
If boundaries are unclear, infer a reasonable structure and separate the content into clear sections.

For each section:

First line: one relevant emoji + one concise section title in {lang}, separated by a single space.
Second line: the reorganized content in {lang}, preserving the core message and key details.
If the original section already has a title or emoji, revise the title if needed and choose a new emoji that better matches the reorganized content.

Special cases:

If the input text is empty, output exactly:
  [No content provided]

Final checks:

Ensure all content is translated into {lang}.
Ensure every requirement above is satisfied.
Make only minimal revisions during final review.

ALL output MUST be written entirely in {lang}.

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

    logger.info("Formatted article: %s", article)
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
