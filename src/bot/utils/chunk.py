from chonkie import RecursiveChunker


def recursive_chunk(text: str, chunk_size: int = 200_000) -> list[str]:
    chunker = RecursiveChunker(
        tokenizer="character",
        chunk_size=chunk_size,
    )
    chunks = chunker.chunk(text)
    return [chunk.text for chunk in chunks]
