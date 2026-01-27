from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Protocol

from aiogram.types import Message


class CallbackProtocol(Protocol):
    """Protocol for all bot callbacks.

    This protocol allows both function-based and class-based callbacks,
    as long as they follow the standard aiogram callback signature.

    Examples:
        # Function-based callback
        async def my_callback(message: Message) -> None:
            ...

        # Class-based callback
        class MyCallback:
            async def __call__(self, message: Message) -> None:
                ...
    """

    async def __call__(self, message: Message) -> None:
        """Handle a Telegram message.

        Args:
            message: The Telegram message to process
        """
        ...


class BaseCallback(ABC):
    """Abstract base class for class-based callbacks.

    This class provides a foundation for callbacks that need:
    - State management (e.g., language, configuration)
    - Shared functionality
    - Complex initialization

    For simple, stateless callbacks, prefer using functions instead.
    """

    @abstractmethod
    async def __call__(self, message: Message) -> None:
        """Handle a Telegram message.

        Args:
            message: The Telegram message to process
        """
