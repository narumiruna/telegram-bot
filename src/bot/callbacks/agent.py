from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import cast

from agents import Agent
from agents import Runner
from agents import TResponseInputItem
from agents import trace
from agents.mcp.server import MCPServerStdio
from agents.mcp.server import MCPServerStdioParams
from loguru import logger
from mcp.client.stdio import StdioServerParameters
from telegram import Message
from telegram import Update
from telegram.ext import ContextTypes
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt

from ..cache import get_cache_from_env
from ..constants import CACHE_TTL_SECONDS
from ..constants import MCP_CLEANUP_TIMEOUT
from ..constants import MCP_CONNECT_TIMEOUT
from ..model import get_openai_model
from ..model import get_openai_model_settings
from ..retry_utils import is_retryable_error
from ..tools import query_rate_history
from ..utils import async_load_url
from ..utils import load_json
from ..utils import parse_url
from .utils import get_message_text
from .utils import safe_callback

INSTRUCTIONS = """
你是一位台灣繁體中文的資訊查詢助理，請根據使用者問題查詢並提供正確、可靠且經查證的資訊，嚴禁捏造或猜測答案，並協助釐清需求。遇到資訊不足時，請主動向使用者詢問以釐清需求。回應僅能依工具查證到的資料，嚴格禁止自行推測、回憶或捏造。回應前，請完整規劃與反思思考步驟，不可略過。

【核心指引】
- 所有回應必須使用台灣繁體中文，保持專業、簡潔、明確。
- 嚴禁捏造、推測或依記憶作答，只能根據查詢結果或工具取得的資訊回應。
- 必須善用合適的外部工具（例如網路搜尋、資料庫等）查詢資料。
- 若查無任何相關資料，請主動告知使用者，並釐清需求或請求更多細節，不得填補內容。
- 每個思考步驟僅保留最多5字簡要草稿，無需詳細展開。
- 回應內容僅允許文字格式，每段開頭須加適當表情符號及簡潔標題，標題需直觀反映主旨。
- 嚴格禁止使用粗體、斜體、標題格式或清單符號。
- 日食/日本美食詢問時，優先使用 gurume mcp 工具查詢。
  針對「有哪些好吃的」等美食搜尋，請自動根據語意抽取合適的「area」及「keyword」進行查詢，若未特別指定則留空。
- gurume mcp 查餐範例如下（請按規則處理）：
  - 你是專為食べログ搜尋最佳化的日文自然語言處理模型。
    根據下方使用者輸入，抽取搜尋用的「area（エリア）」與「keyword（キーワード）」，回傳日文。若找不到則回空字串。
  - 鍵："area"、"keyword"，值必須日文，地名簡潔明確，類型/菜名精準。如找不到資訊則空字串。
    - 「我想吃三重的壽喜燒」→ area: "三重", keyword: "すき焼き"
    - 「台北的拉麵」→ area: "台北", keyword: "ラーメン"
    - 「sushi in Tokyo」→ area: "東京", keyword: "寿司"
    - 「大阪難波附近的居酒屋」→ area: "大阪難波", keyword: "居酒屋"

【標準思考步驟】
1. 理解問題（5字內草稿）
2. 規劃查詢（5字內草稿）
3. 執行查詢（5字內草稿）
4. 整理資訊（5字內草稿）
5. 產生回應（5字內草稿）

【回答規範】
- 僅能用文字陳述，逐段回應。
- 每段開頭必須加表情符號及概括主題的標題（正文前）。
- 禁止任何粗體、斜體、標題符號或清單格式。
- 若查無資料或不確定查詢方式，請主動請求使用者提供更多細節。

# Steps
1. 釐清用戶需求與問題核心
2. 規劃並選擇最合適的工具（如 gurume mcp 查日食）
3. 具體列出所有查詢與思考過程（每步最精簡草稿）
4. 執行資料查詢並核實來源
5. 依規範整理與產生回覆，每段開頭加表情符號＋主旨標題

# Output Format

請以純文字格式逐段呈現，每段前方加表情符號與本段主旨標題，內文用台灣繁體中文完整敘述。禁止使用粗體、斜體、標題格式或清單。

# Examples

【查日本美食】
輸入：「東京好吃的拉麵有哪些？」
- 步驟草稿：理解問題→規劃搜尋→查詢gurume mcp→整理餐廳名單→產生回應
- 正確回應：
😋 拉麵推薦
以下是東京幾家知名拉麵店：○○拉麵、△△拉麵。這些餐廳以湯頭濃厚、口味道地聞名，建議提前預約。
🤔 資訊來源
資料來自 gurume mcp 工具查詢結果，如需其他地區或料理請補充說明。

【資訊不足情境】
輸入：「請推薦附近景點」
- 步驟草稿：辨識地點→發現資訊不足→主動詢問→等待用戶補充
- 正確回應：
❓ 需要地點
請問您目前所在的城市或地區為何？提供地點後我才能推薦周邊景點。

（現實案例應根據實際查詢結果或使用工具資訊產生，以上為格式與流程示意。）

# Notes
- 起始每次回應前，務必先釐清與核查所有資訊來源，保證無任何臆測或捏造內容。
- 如遇需求模糊、查無資料、必須補齊資訊時，請務必主動說明並協助用戶釐清。
- 回應時請嚴格遵守純文字、段首表情符號加標題之格式。
- 回應流程以「規劃・查證後回答」為核心，每步思考要留（最長5字）草稿以自我檢查。

重要提醒：必須徹底遵守先規劃反思、依工具查證、嚴禁幻想與推測等原則，每段開頭須加表情符號＋簡要主題。
""".strip()


def load_mcp_config(f: str | Path) -> dict[str, StdioServerParameters]:
    data = load_json(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration file: {f}")

    result = {}
    for name, params in data.items():
        if not isinstance(params, dict):
            raise ValueError(f"Invalid parameters for {name}: {params}")

        env_vars = params.get("env")
        if isinstance(env_vars, dict):
            for k, v in env_vars.items():
                if v == "":
                    env_vars[k] = os.getenv(k, "")

        result[name] = StdioServerParameters.model_validate(params)
    return result


def remove_tool_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    """Remove tool-related messages from the message list.

    Args:
        messages: List of response input items

    Returns:
        Filtered list without tool messages
    """
    tool_types = {
        "function_call",
        "function_call_output",
        "computer_call",
        "computer_call_output",
        "file_search_call",
        "web_search_call",
    }
    return [msg for msg in messages if msg.get("type") not in tool_types]


def remove_fake_id_messages(messages: list[TResponseInputItem]) -> list[TResponseInputItem]:
    """Remove messages with fake IDs from the message list.

    Args:
        messages: List of response input items

    Returns:
        Filtered list without fake ID messages
    """
    return [msg for msg in messages if msg.get("id") != "__fake_id__"]


class AgentCallback:
    def _make_cache_key(self, message_id: int, chat_id: int) -> str:
        """Generate a cache key for storing conversation history.

        Args:
            message_id: The Telegram message ID
            chat_id: The Telegram chat ID

        Returns:
            A cache key string
        """
        return f"bot:{message_id}:{chat_id}"

    @classmethod
    def from_config(cls, config_file: str | Path) -> AgentCallback:
        """Create AgentCallback from MCP server configuration file.

        Args:
            config_file: Path to the MCP server configuration JSON file

        Returns:
            Configured AgentCallback instance
        """
        config = load_mcp_config(config_file)

        # Read configuration from environment variables
        mcp_timeout = int(os.getenv("MCP_SERVER_TIMEOUT", "300"))
        max_cache_size = int(os.getenv("AGENT_MAX_CACHE_SIZE", "50"))

        agent = Agent(
            name="agent",
            instructions=INSTRUCTIONS,
            model=get_openai_model(),
            model_settings=get_openai_model_settings(),
            tools=[query_rate_history],
            mcp_servers=[
                MCPServerStdio(
                    params=cast(MCPServerStdioParams, params.model_dump()),
                    name=name,
                    client_session_timeout_seconds=mcp_timeout,
                )
                for name, params in config.items()
            ],
        )
        return cls(agent, max_cache_size=max_cache_size)

    def __init__(self, agent: Agent, max_cache_size: int = 50) -> None:
        """Initialize AgentCallback.

        Args:
            agent: The Agent instance to use
            max_cache_size: Maximum number of messages to keep in cache (default: 50)
        """
        self.agent = agent

        # max_cache_size is the maximum number of messages to keep in the cache
        self.max_cache_size = max_cache_size

        # message.chat.id -> list of messages
        self.cache = get_cache_from_env()

    async def connect(self) -> None:
        """Connect to all MCP servers with timeout.

        Continues to connect remaining servers even if some fail.
        Connection timeout is enforced to prevent hanging.
        """
        for mcp_server in self.agent.mcp_servers:
            try:
                logger.info(
                    "Connecting to MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CONNECT_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.connect(), timeout=MCP_CONNECT_TIMEOUT)
                logger.info("Successfully connected to MCP server: {name}", name=mcp_server.name)
            except TimeoutError:
                logger.error(
                    "Connection timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=MCP_CONNECT_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to MCP server {name}: {error}",
                    name=mcp_server.name,
                    error=str(e),
                )

    async def cleanup(self) -> None:
        """Cleanup all MCP servers with timeout.

        Continues to cleanup remaining servers even if some fail.
        Cleanup timeout is enforced to prevent hanging.
        """
        for mcp_server in self.agent.mcp_servers:
            try:
                logger.info(
                    "Cleaning up MCP server: {name} (timeout: {timeout}s)",
                    name=mcp_server.name,
                    timeout=MCP_CLEANUP_TIMEOUT,
                )
                await asyncio.wait_for(mcp_server.cleanup(), timeout=MCP_CLEANUP_TIMEOUT)
                logger.info("Successfully cleaned up MCP server: {name}", name=mcp_server.name)
            except TimeoutError:
                logger.error(
                    "Cleanup timeout for MCP server {name} after {timeout}s",
                    name=mcp_server.name,
                    timeout=MCP_CLEANUP_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    "Failed to cleanup MCP server {name}: {error}",
                    name=mcp_server.name,
                    error=str(e),
                )

    @retry(retry=retry_if_exception(is_retryable_error), stop=stop_after_attempt(3))
    async def _load_url_with_retry(self, url: str) -> str:
        """Load URL content with retry mechanism.

        Args:
            url: The URL to load

        Returns:
            The loaded content

        Raises:
            Exception: If all retry attempts fail
        """
        return await async_load_url(url)

    async def load_url_content(self, message_text: str) -> str:
        """Load URL content from message text if URL is present.

        Args:
            message_text: The message text that may contain a URL

        Returns:
            The message text with URL content replaced (if URL found and loaded successfully)
        """
        parsed_url = parse_url(message_text)
        if not parsed_url:
            return message_text

        try:
            logger.info("Loading URL content: {url}", url=parsed_url)
            url_content = await self._load_url_with_retry(parsed_url)
            logger.info("Successfully loaded URL content: {url}", url=parsed_url)

            message_text = message_text.replace(
                parsed_url,
                f"[URL content from {parsed_url}]:\n'''\n{url_content}\n'''\n[END of URL content]\n",
                1,
            )
        except Exception as e:
            logger.error("Failed to load URL {url}: {error}", url=parsed_url, error=str(e))
            # Return original message text if URL loading fails
            logger.info("Falling back to original message text")

        return message_text

    async def handle_message(self, message: Message) -> None:
        """Handle incoming message and generate response.

        Args:
            message: The Telegram message to handle
        """
        message_text = get_message_text(message, include_reply_to_message=True, include_user_name=True)
        if not message_text:
            return

        logger.info("Handling message from chat {chat_id}", chat_id=message.chat.id)

        # if the message is a reply to another message, get the previous messages
        messages = []
        if message.reply_to_message is not None:
            key = self._make_cache_key(message.reply_to_message.id, message.chat.id)
            try:
                logger.debug("Loading conversation history from cache: {key}", key=key)
                messages = await self.cache.get(key, default=[])
                logger.debug("Loaded {count} messages from cache", count=len(messages))
            except Exception as e:
                logger.error("Failed to load from cache: {error}", error=str(e))
                messages = []

        # remove all tool messages from the memory
        messages = remove_tool_messages(messages)
        messages = remove_fake_id_messages(messages)

        # replace the URL with the content
        message_text = await self.load_url_content(message_text)

        # add the user message to the list of messages
        messages.append({"role": "user", "content": message_text})  # ty:ignore[invalid-argument-type]

        # send the messages to the agent
        logger.info("Running agent with {count} messages", count=len(messages))
        result = await Runner.run(self.agent, input=messages)
        logger.info("Agent completed. New items: {new_items}", new_items=result.new_items)

        # update the memory
        input_items = result.to_input_list()
        if len(input_items) > self.max_cache_size:
            logger.debug("Trimming conversation history to {size} items", size=self.max_cache_size)
            input_items = input_items[-self.max_cache_size :]

        new_message = await message.reply_text(result.final_output)
        new_key = self._make_cache_key(new_message.id, message.chat.id)

        # Save conversation history to cache with TTL
        try:
            logger.debug(
                "Saving conversation history to cache: {key} with TTL {ttl}s",
                key=new_key,
                ttl=CACHE_TTL_SECONDS,
            )
            await self.cache.set(new_key, input_items, ttl=CACHE_TTL_SECONDS)
            logger.debug("Successfully saved conversation history")
        except Exception as e:
            logger.error("Failed to save to cache: {error}", error=str(e))

    @safe_callback
    async def handle_command(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return

        with trace("handle_command"):
            await self.handle_message(update.message)

    @safe_callback
    async def handle_reply(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if (
            update.message is None
            or update.message.reply_to_message is None
            or update.message.reply_to_message.from_user is None
            or not update.message.reply_to_message.from_user.is_bot
        ):
            return

        with trace("handle_reply"):
            await self.handle_message(update.message)
