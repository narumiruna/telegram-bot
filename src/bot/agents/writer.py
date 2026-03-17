import asyncio

from agents import Agent
from agents import Runner

from bot.core.message_response import MessageResponse
from bot.core.prompt_template import PromptTemplate
from bot.provider import get_openai_model
from bot.utils.chunk import chunk_on_delimiter

INSTRUCTIONS = PromptTemplate(
    template="""
Extract, reorganize, and translate the input text into {lang} as a readable blog post.
Do not fabricate, infer, or add any information beyond the input.
Preserve all important points from the input while improving clarity and flow.

Generate a clear, specific blog post title in {lang} that reflects the reorganized key points and important content.
Do not use generic titles such as “Article” or “Summary”.

Rewrite the content as a professional, neutral blog post in plain and accessible language.
Prioritize readability and coherent narrative flow for general readers.
If the input is legal, technical, or otherwise complex, simplify wording while preserving essential facts and meaning.

Output rules:

Respond in plain text only.
Do not use Markdown, HTML, or any markup syntax.

Structure rules:

The output must follow this order:
1) Title line in {lang}
2) Lead paragraph in {lang}
3) Body paragraphs in {lang}, arranged in logical order
4) Closing paragraph in {lang}
Do not use emojis, bullet markers, numbered list markers, or section labels.
Maintain smooth transitions between paragraphs and keep the full post cohesive.

Special cases:

If the input text is empty, output exactly:
  [No content provided]

Final checks:

Ensure the output is a complete, readable blog post with title, lead, body, and closing.
Ensure all important points from the input are preserved without adding new facts.
Ensure all content is translated into {lang} and written in a professional, neutral tone.
Ensure every requirement above is satisfied.
Make only minimal revisions during final review.

ALL output MUST be written entirely in {lang}.
""",  # noqa: E501
)


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
