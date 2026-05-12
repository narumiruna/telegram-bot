from __future__ import annotations

from typing import Literal

from agents import Model
from agents import OpenAIChatCompletionsModel
from agents import OpenAIResponsesModel
from openai import AsyncOpenAI

from .settings import settings


def get_openai_model(api_type: Literal["responses", "chat_completions"] = "responses") -> Model:
    model_name = settings.openai_model

    client = AsyncOpenAI()

    match api_type:
        case "responses":
            return OpenAIResponsesModel(model_name, openai_client=client)
        case "chat_completions":
            return OpenAIChatCompletionsModel(model_name, openai_client=client)
        case _:
            raise ValueError(f"Invalid API type: {api_type}")
