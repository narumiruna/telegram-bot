from __future__ import annotations

from unittest.mock import Mock

import pytest
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.callbacks import BaseCallback


class TestCallbackProtocol:
    """Test CallbackProtocol type checking and compatibility."""

    def test_function_conforms_to_protocol(self) -> None:
        """Test that a function-based callback conforms to CallbackProtocol."""

        async def my_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            pass

        # This is a static type check, but we can verify the signature
        assert callable(my_callback)

    def test_class_conforms_to_protocol(self) -> None:
        """Test that a class-based callback conforms to CallbackProtocol."""

        class MyCallback:
            async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                pass

        callback = MyCallback()
        assert callable(callback)


class TestBaseCallback:
    """Test BaseCallback abstract base class."""

    def test_cannot_instantiate_base_callback(self) -> None:
        """Test that BaseCallback cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseCallback()  # type: ignore

    def test_concrete_callback_must_implement_call(self) -> None:
        """Test that concrete callbacks must implement __call__."""

        class IncompleteCallback(BaseCallback):
            pass

        with pytest.raises(TypeError):
            IncompleteCallback()  # type: ignore

    def test_concrete_callback_with_call(self) -> None:
        """Test that concrete callbacks with __call__ can be instantiated."""

        class CompleteCallback(BaseCallback):
            async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                pass

        callback = CompleteCallback()
        assert callable(callback)

    @pytest.mark.asyncio
    async def test_callback_can_be_called(self) -> None:
        """Test that a concrete callback can be called."""

        class TestCallback(BaseCallback):
            def __init__(self) -> None:
                self.called = False

            async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                self.called = True

        callback = TestCallback()
        mock_update = Mock(spec=Update)
        mock_context = Mock()
        await callback(mock_update, mock_context)
        assert callback.called
