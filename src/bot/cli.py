import typer
from dotenv import find_dotenv
from dotenv import load_dotenv

from .bot import run_bot
from .utils import configure_langfuse


def main():
    load_dotenv(find_dotenv(raise_error_if_not_found=True, usecwd=True))
    configure_langfuse()
    typer.run(run_bot)
