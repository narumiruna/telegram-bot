from __future__ import annotations

from agents import OpenAIResponsesModel
from openai import AsyncOpenAI

from .settings import settings


def get_openai_model() -> OpenAIResponsesModel:
    return OpenAIResponsesModel(settings.openai_model, openai_client=AsyncOpenAI())
