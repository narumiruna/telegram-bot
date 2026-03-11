from aiogram.types import Message

from bot.settings import settings


async def show_model_callback(message: Message) -> None:
    await message.answer(f"current model: {settings.openai_model}")


async def set_model_callback(message: Message) -> None:
    message_text = message.text or ""
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("usage: /setmodel <model_name>")
        return

    settings.openai_model = parts[1].strip()

    await message.answer(f"model updated to: {settings.openai_model}")
