import asyncio
from functools import cache

from agents import Agent
from agents import Runner

from bot.core.presentation import MessageResponse
from bot.core.prompt_template import PromptTemplate
from bot.provider import get_openai_model
from bot.utils.chunk import chunk_on_delimiter

INSTRUCTIONS = PromptTemplate(
    template="""
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
""",  # noqa: E501
)


@cache
def build_writer_agent(lang: str = "台灣正體中文") -> Agent:
    return Agent(
        "writer-agent",
        model=get_openai_model(),
        instructions=INSTRUCTIONS.render(lang=lang),
        output_type=MessageResponse,
    )


async def _write(text: str) -> MessageResponse:
    agent = build_writer_agent()
    result = await Runner.run(agent, input=text)
    return result.final_output_as(MessageResponse)


async def write_article(text: str) -> MessageResponse:
    chunks = chunk_on_delimiter(text)
    if len(chunks) == 1:
        return await _write(text)

    articles = await asyncio.gather(*[_write(chunk) for chunk in chunks])
    return await _write("\n\n".join([article.content for article in articles]))
