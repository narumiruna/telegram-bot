from typing import Any

from agents import Agent
from agents import Model
from agents import ModelSettings
from agents import Runner

from .model import get_openai_model
from .model import get_openai_model_settings


async def lazy_run(
    input: str,
    name: str = "lazy_run",
    instructions: str | None = None,
    model: Model | None = None,
    model_settings: ModelSettings | None = None,
    output_type: type[Any] | None = None,
) -> Any:
    model = model or get_openai_model()
    model_settings = model_settings or get_openai_model_settings()
    result = await Runner.run(
        starting_agent=Agent(
            name=name,
            instructions=instructions,
            model=model,
            model_settings=model_settings,
            output_type=output_type,
        ),
        input=input,
    )
    return result.final_output
