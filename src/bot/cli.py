import asyncio

from dotenv import find_dotenv
from dotenv import load_dotenv

from .bot import run_bot
from .utils.observability import configure_logging


def main() -> None:
    load_dotenv(
        find_dotenv(
            raise_error_if_not_found=True,
            usecwd=True,
        ),
        override=True,
    )
    configure_logging()
    asyncio.run(run_bot())
