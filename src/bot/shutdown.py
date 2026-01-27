from __future__ import annotations

import asyncio
import signal
from collections.abc import Iterable

from loguru import logger


class ShutdownManager:
    def __init__(self, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds
        self._event = asyncio.Event()

    @property
    def event(self) -> asyncio.Event:
        return self._event

    def install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.trigger, sig)
            except (NotImplementedError, RuntimeError):
                logger.warning("Signal handlers are not supported in this runtime.")
                break

    def trigger(self, sig: signal.Signals | None = None) -> None:
        if self._event.is_set():
            return
        signal_name = sig.name if isinstance(sig, signal.Signals) else "unknown"
        logger.info("Received shutdown signal: {signal}", signal=signal_name)
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()

    async def cancel_tasks(self, tasks: Iterable[asyncio.Task], *, reason: str) -> None:
        pending = [task for task in tasks if task is not None and not task.done()]
        if not pending:
            return

        logger.info("Cancelling {count} task(s) due to {reason}", count=len(pending), reason=reason)
        for task in pending:
            task.cancel()

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            logger.warning(
                "Timeout waiting for {count} task(s) to cancel",
                count=len(pending),
            )
            return

        for result in results:
            if isinstance(result, asyncio.CancelledError):
                continue
            if isinstance(result, BaseException):
                logger.opt(exception=result).error("Task error during {reason}", reason=reason)
