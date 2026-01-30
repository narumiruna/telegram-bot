from __future__ import annotations

from functools import cache
from typing import Literal

from agents import Model
from agents import ModelSettings
from agents import OpenAIChatCompletionsModel
from agents import OpenAIResponsesModel
from agents.extensions.models.litellm_model import LitellmModel
from openai import AsyncAzureOpenAI
from openai import AsyncOpenAI

from .settings import settings


@cache
def get_openai_client() -> AsyncOpenAI:
    if settings.azure_openai_api_key:
        return AsyncAzureOpenAI()
    return AsyncOpenAI()


@cache
def get_openai_model(api_type: Literal["responses", "chat_completions"] = "responses") -> Model:
    model_name = settings.openai_model

    # https://openai.github.io/openai-agents-python/models/litellm/
    if settings.litellm_api_key:
        return LitellmModel(model=model_name, api_key=settings.litellm_api_key)

    client = get_openai_client()

    match api_type:
        case "responses":
            return OpenAIResponsesModel(model_name, openai_client=client)
        case "chat_completions":
            return OpenAIChatCompletionsModel(model_name, openai_client=client)
        case _:
            raise ValueError(f"Invalid API type: {api_type}")


@cache
def get_openai_model_settings() -> ModelSettings:
    return ModelSettings(
        # temperature=settings.openai_temperature,
        tool_choice="auto",
    )
