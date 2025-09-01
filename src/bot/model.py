from __future__ import annotations

import os
from functools import cache
from typing import Literal

import logfire
from agents import Model
from agents import ModelSettings
from agents import OpenAIChatCompletionsModel
from agents import OpenAIResponsesModel
from agents.extensions.models.litellm_model import LitellmModel
from openai import AsyncAzureOpenAI
from openai import AsyncOpenAI

from .utils import logfire_is_enabled


@cache
def get_openai_client() -> AsyncOpenAI:
    azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if azure_api_key:
        return AsyncAzureOpenAI()
    return AsyncOpenAI()


@cache
def get_openai_model(api_type: Literal["responses", "chat_completions"] = "responses") -> Model:
    model_name = os.getenv("OPENAI_MODEL", "gpt-4.1")

    # https://openai.github.io/openai-agents-python/models/litellm/
    litellm_api_key = os.getenv("LITELLM_API_KEY")
    if litellm_api_key:
        return LitellmModel(model=model_name, api_key=litellm_api_key)

    client = get_openai_client()

    if logfire_is_enabled():
        logfire.instrument_openai(client)

    match api_type:
        case "responses":
            return OpenAIResponsesModel(model_name, openai_client=client)
        case "chat_completions":
            return OpenAIChatCompletionsModel(model_name, openai_client=client)
        case _:
            raise ValueError(f"Invalid API type: {api_type}")


@cache
def get_openai_model_settings() -> ModelSettings:
    temperature = float(os.getenv("OPENAI_TEMPERATURE", 0.0))
    return ModelSettings(temperature=temperature)
