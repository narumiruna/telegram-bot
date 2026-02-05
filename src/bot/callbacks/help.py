from aiogram.types import Message


async def help_callback(message: Message) -> None:
    await message.answer(
        "\n".join(
            [
                "code: https://github.com/narumiruna/telegram-bot",
                "/help - Show this help message",
                "/a - An agent that can assist with various tasks",
                "/s - Summarize a document or URL content",
                "/jp - Translate text to Japanese",
                "/tc - Translate text to Traditional Chinese",
                "/en - Translate text to English",
                "/echo - Echo the message",
                "/yt - Search YouTube",
                "/t - Query ticker from Yahoo Finance and Taiwan stock exchange",
                "/f - Format and normalize the document in 台灣話",
            ]
        ),
        disable_web_page_preview=True,
    )
