from aiogram.types import Message

from bot.settings import settings

_AVAILABLE_MODELS: list[str] = [
    "gpt-4.1",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5.1-codex-mini",
    "gpt-5.3-codex",
    "gpt-5.4",
]


async def _show_usage(message: Message) -> None:
    await message.answer("usage: /setmodel <model_name>")


async def show_model_callback(message: Message) -> None:
    await message.answer(f"current model: {settings.openai_model}")


async def set_model_callback(message: Message) -> None:
    if not message.text:
        await _show_usage(message)
        return

    splitted = message.text.split(maxsplit=1)
    if len(splitted) < 2:
        await _show_usage(message)
        return

    model_name = splitted[1].strip()
    if model_name not in _AVAILABLE_MODELS:
        await message.answer(f"invalid model name: {model_name}\navailable models: {', '.join(_AVAILABLE_MODELS)}")
        return

    settings.openai_model = model_name

    await message.answer(f"model updated to: {settings.openai_model}")
