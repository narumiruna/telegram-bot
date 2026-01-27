from __future__ import annotations

from datetime import UTC
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import httpx
from agents import function_tool
from loguru import logger
from pydantic import BaseModel
from pydantic import field_validator
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from tenacity import wait_random

from bot.retry_utils import is_retryable_error


# {"source":"EUR","target":"USD","value":1.05425,"time":1697653800557}
class Rate(BaseModel):
    source: str
    target: str
    value: float
    time: datetime

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: int | datetime) -> datetime:
        match v:
            case datetime():
                return v
            case int():
                return datetime.fromtimestamp(v // 1000, tz=UTC)
            case _:
                msg = f"invalid time: {v}"
                raise TypeError(msg)

    def __str__(self) -> str:
        time_str = self.time.astimezone(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
        return f"{self.source}/{self.target}: {self.value} at {time_str}"


class Resolution(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"


class Unit(str, Enum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class RateRequest(BaseModel):
    source: str
    target: str

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    def do(self) -> Rate:
        resp = httpx.get(
            url="https://wise.com/rates/live",
            params=self.model_dump(),
            timeout=30.0,
        )
        resp.raise_for_status()
        return Rate.model_validate(resp.json())

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def async_do(self) -> Rate:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url="https://wise.com/rates/live",
                params=self.model_dump(),
            )
            resp.raise_for_status()
            return Rate.model_validate(resp.json())


# https://wise.com/rates/history?source=EUR&target=USD&length=10&resolution=daily&unit=day
class RateHistoryRequest(BaseModel):
    source: str
    target: str
    length: int
    resolution: Resolution
    unit: Unit

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    def do(self) -> list[Rate]:
        resp = httpx.get(
            url="https://wise.com/rates/history",
            params=self.model_dump(mode="json"),
            timeout=30.0,
        )
        resp.raise_for_status()
        return [Rate.model_validate(data) for data in resp.json()]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def async_do(self) -> list[Rate]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url="https://wise.com/rates/history",
                params=self.model_dump(mode="json"),
            )
            resp.raise_for_status()
            return [Rate.model_validate(data) for data in resp.json()]


@function_tool
async def query_rate(source: str, target: str) -> str:
    """Query the exchange rate between two currencies.

    Args:
        source (str): The source currency code (e.g., "EUR").
        target (str): The target currency code (e.g., "USD").
    """
    logger.debug(f"Querying rate for {source} to {target}")

    req = RateRequest(source=source, target=target)
    rate = await req.async_do()
    return rate.model_dump_json()


@function_tool
async def query_rate_history(source: str, target: str, length: int, resolution: Resolution, unit: Unit) -> str:
    """Query the exchange rate history between two currencies.

    Args:
        source (str): The source currency code (e.g., "EUR").
        target (str): The target currency code (e.g., "USD").
        length (int): The number of data points to retrieve.
        resolution (Resolution): The resolution of the data points.
        unit (Unit): The unit of time for the data points.
    """
    logger.debug(f"Querying rate history for {source} to {target}")

    req = RateHistoryRequest(
        source=source,
        target=target,
        length=length,
        resolution=resolution,
        unit=unit,
    )
    rates = await req.async_do()
    return "\n".join([str(rate) for rate in rates])
