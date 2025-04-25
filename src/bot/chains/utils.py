def chunk_on_delimiter(text: str, delimiter: str = " ", max_length: int = 200_000) -> list[str]:
    chunks = []
    current_chunk = ""
    for word in text.split(delimiter):
        if len(current_chunk) + len(word) + len(delimiter) <= max_length:
            current_chunk += word + delimiter
        else:
            chunks.append(current_chunk)
            current_chunk = word + delimiter
    if current_chunk:
        chunks.append(current_chunk)
    return chunks
