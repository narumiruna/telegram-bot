import logging
import asyncio
from textwrap import dedent


from bot.core.prompting import PromptSpec
from bot.lazy import lazy_run

from .instructions import BASE_INSTRUCTIONS
from .utils import chunk_on_delimiter

logger = logging.getLogger(__name__)

URL_CHUNK_REWRITE_PROMPT = PromptSpec(
    id="rewrite_url_chunk",
    version=1,
    name="rewrite_url_chunk",
    input_template="""
你是一位內容改寫專家。請將以下網頁內容片段改寫成精確、簡潔的文章段落，保持所有重要資訊。

要求：
- 保持原文的完整資訊和細節，不要遺漏關鍵內容
- 改善語句結構和表達方式，使內容更加清晰易懂
- 移除冗餘表述，但保留所有重要事實和數據
- 維持客觀中立的語氣
- 輸出長度控制在原內容的 60-80%
- 使用台灣正體中文

網頁內容片段：
```
{text}
```
""",
)

URL_FINAL_REWRITE_PROMPT = PromptSpec(
    id="create_final_url_rewrite",
    version=1,
    name="create_final_url_rewrite",
    input_template="""
你是一位內容整合專家。請將以下改寫後的網頁段落整合成一篇連貫、精確的完整文章。

要求：
- 將所有段落無縫整合，保持邏輯流暢性
- 確保內容的完整性和連貫性，避免重複
- 維持專業、客觀的寫作風格
- 最終輸出應該是一篇完整的文章，而非摘要
- 輸出長度控制在 2000 字以內，根據內容複雜度調整
- 使用台灣正體中文

改寫後的網頁段落：
{chunks_rewrite}
""",
)


async def rewrite_url_chunk(text: str) -> str:
    """Rewrite a single URL content chunk to be more concise and precise.

    Args:
        text: The URL content chunk to rewrite

    Returns:
        str: Rewritten content in Traditional Chinese
    """
    return await lazy_run(
        input=dedent(URL_CHUNK_REWRITE_PROMPT.render_input(text=text)),
        instructions=URL_CHUNK_REWRITE_PROMPT.render_instructions(BASE_INSTRUCTIONS),
        name=URL_CHUNK_REWRITE_PROMPT.name or "lazy_run",
    )


async def process_url_content(text: str) -> str:
    """Process URL content with chunking and rewriting.

    For long URL content that exceeds the chunk limit, the content is split into chunks,
    each chunk is rewritten for clarity and conciseness, then the rewritten chunks
    are integrated into a coherent article.

    Args:
        text: The URL content to process

    Returns:
        str: Processed and rewritten content in Traditional Chinese
    """
    # Use a reasonable chunk size for URL content (smaller than notes.py default)
    chunks = chunk_on_delimiter(text, max_length=10_000)

    logger.info(
        "Processing URL content: {chunks} chunks from {length} characters", chunks=len(chunks), length=len(text)
    )

    if len(chunks) <= 1:
        # For short or empty content, return original as-is
        logger.info("Short URL content detected, returning original content")
        return text

    # For long content, rewrite each chunk in parallel
    logger.info("Long URL content detected, processing {chunks} chunks in parallel", chunks=len(chunks))

    chunk_rewrites = await asyncio.gather(*[rewrite_url_chunk(chunk) for chunk in chunks])

    # Combine rewrites and create final integrated article
    chunks_rewrite = "\n\n".join([f"段落 {i + 1}:\n{rewrite}" for i, rewrite in enumerate(chunk_rewrites)])

    final_rewrite = await lazy_run(
        input=dedent(URL_FINAL_REWRITE_PROMPT.render_input(chunks_rewrite=chunks_rewrite)),
        instructions=URL_FINAL_REWRITE_PROMPT.render_instructions(BASE_INSTRUCTIONS),
        name=URL_FINAL_REWRITE_PROMPT.name or "lazy_run",
    )

    logger.info(
        "URL content processing completed: {input_length} -> {output_length} characters",
        input_length=len(text),
        output_length=len(final_rewrite),
    )

    return final_rewrite
