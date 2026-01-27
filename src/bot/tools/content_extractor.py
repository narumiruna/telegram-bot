from agents import function_tool

from bot.utils import load_url


@function_tool
async def extract_content_from_url(url: str) -> str:
    """Extract the main content from a url, including youtube/reel transcripts, pdf, and html content, ...

    Args:
        url: The URL of the webpage to extract the content from.

    Returns:
        The extracted content as a string.
    """
    return await load_url(url)
