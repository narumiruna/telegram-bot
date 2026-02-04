from aiogram.types import Message
from pydantic import BaseModel

from bot.core.presentation import MessageResponse


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

    async def answer(self, message: Message, with_title: bool = True) -> None:
        response = MessageResponse(
            content=self.content,
            title=self.title if with_title else None,
            parse_mode=None,  # Plain text
        )
        await response.send(message)
