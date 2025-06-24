def chunk_on_delimiter(text: str, delimiter: str = " ", max_length: int = 200_000) -> list[str]:
    """Split text into chunks based on a delimiter while respecting max length.

    Args:
        text: The text to chunk
        delimiter: The delimiter to split on (default: space)
        max_length: Maximum length of each chunk (default: 200,000)

    Returns:
        List of text chunks

    Raises:
        ValueError: If max_length is less than 1
    """
    if max_length < 1:
        raise ValueError("max_length must be at least 1")

    if not text:
        return []

    chunks = []
    current_chunk = ""
    delimiter_len = len(delimiter)

    for word in text.split(delimiter):
        # Check if adding this word would exceed max_length
        potential_length = len(current_chunk) + len(word) + delimiter_len

        if potential_length <= max_length:
            current_chunk += word + delimiter
        else:
            # If we have a current chunk, save it
            if current_chunk:
                chunks.append(current_chunk.rstrip(delimiter))

            # Handle case where single word is longer than max_length
            if len(word) > max_length:
                # Split the word itself
                for i in range(0, len(word), max_length):
                    chunks.append(word[i : i + max_length])
                current_chunk = ""
            else:
                current_chunk = word + delimiter

    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(current_chunk.rstrip(delimiter))

    return chunks
