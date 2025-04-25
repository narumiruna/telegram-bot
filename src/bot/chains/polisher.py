from pydantic import BaseModel
from pydantic import Field

from ..lazy import parse


class PolishedText(BaseModel):
    polished_text: str = Field(..., description="The polished text.")
    detected_language: str = Field(..., description="The detected language of the input text.")

    def __str__(self) -> str:
        return self.polished_text


SYSTEM_PROMPT = """Your task is to **polish** the input text in any language to enhance clarity, fluency, and professionalism while preserving the original meaning.

## Steps

1. Carefully read the provided text in its original language.
2. Identify unclear phrases, jargon, or ambiguous statements and clarify or simplify them.
3. Rephrase sentences to improve fluency and coherence.
4. Ensure the tone is professional and appropriate for the intended audience.
5. Correct any grammatical, punctuation, and spelling errors.
6. Review the final version for overall flow and readability.
7. If the text is in Simplified Chinese, convert it to Traditional Chinese.

## Guidelines

- Provide a polished version of the text in the same language, maintaining the original meaning while enhancing clarity and professionalism. The length should be similar to the original text.
- Respect the cultural nuances of the language used.
- Avoid introducing new information or altering the fundamental message of the original text.
"""  # noqa


async def polish(text: str) -> str:
    return str(
        await parse(
            input=f"Polish the following text:\n{text}",
            instructions=SYSTEM_PROMPT,
            output_type=PolishedText,
        )
    )
