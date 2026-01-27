import asyncio

import typer
from dotenv import find_dotenv
from dotenv import load_dotenv

from .bot import run_bot
from .utils import configure_logfire


def main() -> None:
    load_dotenv(
        find_dotenv(
            raise_error_if_not_found=True,
            usecwd=True,
        ),
        override=True,
    )
    configure_logfire()
    asyncio.run(run_bot())
