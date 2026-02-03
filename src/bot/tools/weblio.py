import logging
import httpx
from agents import function_tool
from bs4 import BeautifulSoup
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from tenacity import wait_random

from bot.retry_utils import is_retryable_error

logger = logging.getLogger(__name__)


@function_tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
    retry=retry_if_exception(is_retryable_error),
    reraise=True,
)
def query_weblio(query: str) -> str:
    """Fetches the definitions of the query Japanese word from Weblio.

    Args:
        query (str): The Japanese word you want to search for in Weblio.

    Returns:
        str: A string containing the definitions of the word.
    """
    logger.info("Querying Weblio for {query}", query=query)

    url = f"https://www.weblio.jp/content/{query}"
    response = httpx.get(url, timeout=30.0)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    definitions = soup.find_all("div", class_="kiji")
    return "\n".join([definition.text.strip() for definition in definitions])
