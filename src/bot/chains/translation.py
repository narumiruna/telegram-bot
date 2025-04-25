import inspect

from ..lazy import send


async def translate_to_taiwanese(text: str) -> str:
    prompt = f"""
    你是翻譯專家，你會適當的保留專有名詞，並確保翻譯的準確性。將以下的文字翻譯成台灣繁體中文：

    {text}
    """
    return await send(inspect.cleandoc(prompt))


async def translate(text: str, lang: str) -> str:
    user_prompt = f'"""{text}"""'

    system_prompt = f"""
    Translate the text delimited by triple quotation marks into {lang}.
    """.strip()
    result = await send(user_prompt, instructions=system_prompt)
    return result.strip('"')


async def translate_and_explain(text: str, lang: str) -> str:
    user_prompt = f'"""{text}"""'

    system_prompt = f"""
    Translate the text delimited by triple quotation marks into {lang}, and provide a concise explanation of grammar and usage in {lang}, along with example sentences to enhance understanding."
    """.strip()  # noqa

    result = await send(user_prompt, instructions=system_prompt)
    return result.strip('"')
