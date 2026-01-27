import inspect

from bot.core.prompting import PromptSpec
from bot.lazy import lazy_run

from .instructions import BASE_INSTRUCTIONS

TRANSLATE_TO_TAIWANESE_PROMPT = PromptSpec(
    id="translate_to_taiwanese",
    version=1,
    name="translate_to_taiwanese",
    input_template="""
你是翻譯專家，你會適當的保留專有名詞，並確保翻譯的準確性。將以下的文字翻譯成台灣正體中文：

{text}
""",
)

TRANSLATE_PROMPT = PromptSpec(
    id="translate",
    version=1,
    name="translate",
    input_template='"""{text}"""',
    instructions_template="Translate the text delimited by triple quotation marks into {lang}.",
)

TRANSLATE_AND_EXPLAIN_PROMPT = PromptSpec(
    id="translate_and_explain",
    version=1,
    name="translate_and_explain",
    input_template='"""{text}"""',
    instructions_template=(
        "Translate the text delimited by triple quotation marks into {lang}, "
        "and provide a concise explanation of grammar and usage in {lang}, "
        "along with example sentences to enhance understanding."
    ),
)


async def translate_to_taiwanese(text: str) -> str:
    """Translate text to Traditional Chinese (Taiwan).

    Args:
        text: The text to translate

    Returns:
        str: Translated text in Traditional Chinese
    """
    prompt = TRANSLATE_TO_TAIWANESE_PROMPT.render_input(text=text)
    return await lazy_run(
        inspect.cleandoc(prompt),
        instructions=TRANSLATE_TO_TAIWANESE_PROMPT.render_instructions(BASE_INSTRUCTIONS),
        name=TRANSLATE_TO_TAIWANESE_PROMPT.name or "lazy_run",
    )


async def translate(text: str, target_lang: str) -> str:
    """Translate text to the specified language.

    Args:
        text: The text to translate
        target_lang: Target language

    Returns:
        str: Translated text
    """
    user_prompt = TRANSLATE_PROMPT.render_input(text=text)
    instructions = TRANSLATE_PROMPT.render_instructions(BASE_INSTRUCTIONS, lang=target_lang)
    translated_text = await lazy_run(user_prompt, instructions=instructions, name=TRANSLATE_PROMPT.name or "lazy_run")
    return translated_text.strip('"')


async def translate_and_explain(text: str, target_lang: str) -> str:
    """Translate text and provide explanation of grammar and usage.

    Args:
        text: The text to translate
        target_lang: Target language

    Returns:
        str: Translated text with grammar explanation and examples
    """
    user_prompt = TRANSLATE_AND_EXPLAIN_PROMPT.render_input(text=text)
    instructions = TRANSLATE_AND_EXPLAIN_PROMPT.render_instructions(BASE_INSTRUCTIONS, lang=target_lang)
    translated_text = await lazy_run(
        user_prompt,
        instructions=instructions,
        name=TRANSLATE_AND_EXPLAIN_PROMPT.name or "lazy_run",
    )
    return translated_text.strip('"')
