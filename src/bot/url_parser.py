import re


def parse_url(s: str) -> str:
    url_pattern = r"https?://[^\s]+"

    match = re.search(url_pattern, s)
    if match:
        return match.group(0)

    return ""


def parse_urls(s: str) -> list[str]:
    """Parse all URLs from the given string.

    Args:
        s: String that may contain URLs

    Returns:
        List of URLs found in the string
    """
    url_pattern = r"https?://[^\s]+"
    return re.findall(url_pattern, s)
