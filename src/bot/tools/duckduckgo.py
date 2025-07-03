import re

import httpx
from agents import function_tool
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt
from tenacity import wait_exponential
from tenacity import wait_random

from bot.retry_utils import is_retryable_error


@function_tool
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=30) + wait_random(0, 0.1),
    retry=retry_if_exception(is_retryable_error),
    reraise=True,
)
def extract_content(url: str) -> str:
    """Extract the main content from a webpage.

    Args:
        url: The URL of the webpage to extract the content from.

    Returns:
        The extracted content as a string.
    """
    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        unwanted_tags = ["script", "style", "nav", "header", "footer", "aside"]
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile("content|main"))

        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        lines = (line.strip() for line in text.splitlines())
        return "\n".join(line for line in lines if line)
    except Exception as e:
        return f"{type(e)}: Failed to extract content from URL {url}"


@function_tool
def web_search(queries: list[str], max_results_per_query: int = 2) -> str:
    """Performs web searches for given queries and returns URLs.

    Args:
        queries: List of search queries.

    Returns:
        str: Newline-separated URLs from search results or error messages.

    Raises:
        Exception: If web search fails entirely.
    """
    search_history: list[str] = []
    try:
        urls = []
        for query in queries:
            results = DDGS(proxies=None).text(query, max_results=max_results_per_query)

            for result in results:
                link = result["href"]
                try:
                    urls.append(link)
                except Exception as e:
                    urls.append(f"{type(e)}: Failed to parse content from URL {link}")
            search_history.append(query)
        return "\n\n".join(urls)

    except Exception as e:
        return f"{type(e)}: Failed to search the web for text"
