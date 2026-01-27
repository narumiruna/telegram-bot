from datetime import datetime
from zoneinfo import ZoneInfo

from agents import function_tool


@function_tool
def get_current_time() -> str:
    return datetime.now(tz=ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M:%S")
