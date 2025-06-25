import httpx
from agents import function_tool
from bs4 import BeautifulSoup
from loguru import logger

from bot.retry import NETWORK_API_CONFIG
from bot.retry import robust_api_call


@function_tool
@robust_api_call(NETWORK_API_CONFIG, exceptions=(httpx.HTTPError,))
def query_weblio(query: str) -> str:
    """Fetches the definitions of the query Japanese word from Weblio.

    Args:
        query (str): The Japanese word you want to search for in Weblio.

    Returns:
        str: A string containing the definitions of the word.
    """
    logger.info("Querying Weblio for {query}", query=query)

    url = f"https://www.weblio.jp/content/{query}"
    response = httpx.get(url, timeout=NETWORK_API_CONFIG.timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    res = []
    definitions = soup.find_all("div", class_="kiji")
    for definition in definitions:
        res.append(definition.text.strip())
    return "\n".join(res)
