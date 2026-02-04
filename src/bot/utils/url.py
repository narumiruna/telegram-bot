import kabigon
import logfire


async def load_url(url: str) -> str:
    with logfire.span("load_url"):
        return await kabigon.load_url(url)
