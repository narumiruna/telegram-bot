from agents import Agent
from pydantic import BaseModel

from bot.core.presentation import MessageResponse
from bot.core.prompt_template import PromptTemplate
from bot.provider import get_openai_model

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


def build_writer_agent(lang: str = "台灣正體中文") -> Agent:
    return Agent(
        "writer-agent",
        model=get_openai_model(),
        instructions=INSTRUCTIONS.render(lang=lang),
        output_type=Article,
    )
