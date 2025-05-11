from typing import TypeVar

from agents import Agent
from agents import Model
from agents import ModelSettings
from agents import Runner
from pydantic import BaseModel

from .model import get_openai_model
from .model import get_openai_model_settings

TextFormatT = TypeVar("TextFormatT", bound=BaseModel)


async def send(
    input: str,
    name: str = "lazy_run",
    instructions: str | None = None,
    model: Model | None = None,
    model_settings: ModelSettings | None = None,
) -> str:
    model = model or get_openai_model()
    model_settings = model_settings or get_openai_model_settings()
    result = await Runner.run(
        starting_agent=Agent(
            name=name,
            instructions=instructions,
            model=model,
            model_settings=model_settings,
        ),
        input=input,
    )
    return result.final_output


async def parse(input: str, output_type: type[TextFormatT], instructions: str | None = None) -> TextFormatT:
    result = await Runner.run(
        starting_agent=Agent(
            "",
            instructions,
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            output_type=output_type,
        ),
        input=input,
    )
    return result.final_output
