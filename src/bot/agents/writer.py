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
Do not add new facts, entities, events, or claims beyond the input.
Preserve all materially important points from the input while improving clarity and flow.

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
2) One or more content sections in {lang}
Each content section must follow all rules below:
- The first line must be a standalone section heading in this exact pattern: <emoji> <section title>
- The section title must be specific and written in {lang}
- The section body must start on the next line and may contain one or more paragraphs
- Use section heading lines only for section boundaries; do not add extra heading lines inside the same section
- Do not use Markdown, HTML, bullet markers, or numbered list markers as section labels
The final content section must act as the closing section and only restate points already present in earlier sections.
The title line itself must not include an emoji.
Maintain smooth transitions between paragraphs and keep the full post cohesive.

Special cases:

If the input text is empty, output exactly:
  [No content provided]

Final checks:

Ensure the output is a complete, readable blog post with a title and coherent sections, including opening, body, and closing coverage.
Ensure all important points from the input are preserved without adding new facts.
Ensure all content is translated into {lang} and written in a professional, neutral tone.
Ensure every requirement above is satisfied.
Make only minimal revisions during final review.

ALL output MUST be written entirely in {lang}, except the exact special-case literal "[No content provided]".
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
