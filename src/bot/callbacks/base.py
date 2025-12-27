from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Protocol

from telegram import Update
from telegram.ext import ContextTypes


class CallbackProtocol(Protocol):
    """Protocol for all bot callbacks.

    This protocol allows both function-based and class-based callbacks,
    as long as they follow the standard Telegram callback signature.

    Examples:
        # Function-based callback
        async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            ...

        # Class-based callback
        class MyCallback:
            async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                ...
    """

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle a Telegram update.

        Args:
            update: The Telegram update to process
            context: The callback context
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
    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle a Telegram update.

        Args:
            update: The Telegram update to process
            context: The callback context
        """
        pass
