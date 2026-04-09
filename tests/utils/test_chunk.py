import pytest

from bot.utils.chunk import recursive_chunk


def test_chunk_basic_functionality() -> None:
    """Test basic chunking functionality"""
    text = "word1 word2 word3 word4 word5"
    result = recursive_chunk(text, chunk_size=15)
    # Each chunk should be <= 15 characters
    for chunk in result:
        assert len(chunk) <= 15
    # All words should be preserved
    reconstructed = " ".join(result).replace("  ", " ")
    assert "word1" in reconstructed
    assert "word5" in reconstructed


def test_chunk_empty_text() -> None:
    """Test chunking empty text"""
    result = recursive_chunk("", chunk_size=100)
    assert result == []


def test_chunk_single_word() -> None:
    """Test chunking single word"""
    result = recursive_chunk("hello", chunk_size=100)
    assert result == ["hello"]


def test_chunk_word_longer_than_max_length() -> None:
    """Test handling word longer than max_length"""
    long_word = "verylongwordthatexceedsmaxlength"
    result = recursive_chunk(long_word, chunk_size=10)

    # Should split the long word
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= 10

    # Reconstructed text should contain all characters
    reconstructed = "".join(result)
    assert reconstructed == long_word


def test_chunk_max_length_validation() -> None:
    """Test max_length validation"""
    with pytest.raises(ValueError):
        recursive_chunk("test", chunk_size=0)

    with pytest.raises(ValueError):
        recursive_chunk("test", chunk_size=-1)


def test_chunk_preserves_content() -> None:
    """Test that chunking preserves all content"""
    text = "The quick brown fox jumps over the lazy dog"
    result = recursive_chunk(text, chunk_size=20)

    # Join all chunks and normalize spaces
    reconstructed = " ".join(result).strip()
    # Remove extra spaces that might be introduced
    reconstructed = " ".join(reconstructed.split())

    assert reconstructed == text


def test_chunk_respects_max_length() -> None:
    """Test that chunks respect max_length"""
    text = "a " * 100  # 200 characters
    chunk_size = 50
    result = recursive_chunk(text, chunk_size=chunk_size)

    for chunk in result:
        assert len(chunk) <= chunk_size


def test_chunk_edge_case_exact_length() -> None:
    """Test edge case where text exactly fits max_length"""
    text = "exact"  # 5 characters
    result = recursive_chunk(text, chunk_size=5)
    assert result == ["exact"]
