import logging
from typing import Literal

from agents import function_tool
from tripplus import RedemptionRequest

logger = logging.getLogger(__name__)


@function_tool
def search_award(ori: str, dst: str, cabin: Literal["y", "c", "f"], type: Literal["ow", "rt"]) -> str:
    """
    Search for award flight options between two airports.

    Args:
        ori: Origin airport code (e.g., TPE for Taipei, HKG for Hong Kong)
        dst: Destination airport code (e.g., NRT for Tokyo Narita, LAX for Los Angeles)
        cabin: Cabin class, y: economy, c: business, f: first
        type: Redemption type, ow: one way, rt: round trip

    Returns:
        JSON string with redemption options

    Examples:
        >>> search_award("TPE", "NRT", "c", "ow")  # 台北桃園國際機場 to 東京成田機場 商務艙單程
        >>> search_award("LHR", "JFK", "y", "rt")  # 倫敦希斯路機場 to 紐約甘迺迪機場 經濟艙來回
    """
    req = RedemptionRequest(
        ori=ori,
        dst=dst,
        cabin=cabin,
        type=type,
        programs="ALL",
    )
    logger.debug("RedemptionRequest: %s", req)

    resp = req.do().model_dump_json()
    logger.debug("RedemptionResponse: %s", resp)
    return resp
