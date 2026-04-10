import asyncio
import html
import logging

import logfire
from agents import Agent
from agents import Runner
from aiogram.types import Message
from pydantic import BaseModel
from pydantic import Field

from bot.core.prompt_template import PromptTemplate
from bot.provider import get_openai_model
from bot.utils.chunk import recursive_chunk
from bot.utils.page import async_create_page

logger = logging.getLogger(__name__)


INSTRUCTIONS = PromptTemplate(
    template="""
Task:
Convert the input into a coherent blog post written entirely in {lang}. Return output strictly as the given schema.

Hard constraints:
- Preserve all materially important information from the input.
- Do not add new facts, entities, events, numbers, or claims.
- Use a professional, neutral, easy-to-read tone.
- Simplify complex wording when needed, but keep original meaning.
- Summary must be <= 500 characters.
- Each section.content must be <= 1000 characters.
- All content must be less than 5000 characters in total.

Section rules:
- Every section title must be specific and in {lang}.
- Every section emoji must be exactly one emoji.
- Every section body can have one or more paragraphs.
- Keep transitions smooth and the whole post cohesive
- The final section should be a closing section that only restates earlier points.

Final checks:
- Include opening, body, and closing coverage.
- Ensure all content is in {lang}.
- Ensure every constraint is satisfied.
"""  # noqa: E501
)


class Section(BaseModel):
    title: str = Field(..., description="The title of the section.")
    emoji: str = Field(..., description="An emoji to represent the section.")
    content: str = Field(
        ...,
        description=(
            "The content of the section, which may include multiple paragraphs and formatting. "
            "The content should be less than 1000 characters."
        ),
    )


class Article(BaseModel):
    title: str = Field(..., description="The title of the article.")
    summary: str = Field(..., description="A brief summary of the article.")
    sections: list[Section] = Field(..., description="A list of sections in the article.")

    def render_content_text(self) -> str:
        rendered_sections = [f"{section.emoji} {section.title}\n\n{section.content}" for section in self.sections]
        return "\n\n".join(rendered_sections)

    async def create_page(self) -> str:
        text_content = self.render_content_text()
        page_url = await async_create_page(
            self.title,
            html_content=html.escape(text_content).replace("\n", "<br>"),
        )

        logger.info("Telegraph page created: %s", page_url)
        return page_url

    async def answer(self, message: Message, parse_mode: str | None = "HTML") -> Message:
        page_url = await self.create_page()
        return await message.answer(page_url, parse_mode=parse_mode)


async def _write_article(text: str) -> Article:
    with logfire.span(
        "writer._write_article",
        text_length=len(text),
    ):
        agent = Agent(
            "writer-agent",
            model=get_openai_model(),
            instructions=INSTRUCTIONS.render(lang="台灣正體中文"),
            output_type=Article,
        )

        result = await Runner.run(agent, input=text)
        return result.final_output_as(Article)


async def write_article(text: str) -> Article:
    chunks = recursive_chunk(text)
    if len(chunks) == 1:
        return await _write_article(text)

    articles = await asyncio.gather(
        *[_write_article(chunk) for chunk in chunks],
    )
    return await write_article("\n\n".join([article.render_content_text() for article in articles]))
