import pytest

from bot.utils.chunk import chunk_on_delimiter


def test_chunk_basic_functionality() -> None:
    """Test basic chunking functionality"""
    text = "word1 word2 word3 word4 word5"
    result = chunk_on_delimiter(text, delimiter=" ", max_length=15)
    # Each chunk should be <= 15 characters
    for chunk in result:
        assert len(chunk) <= 15
    # All words should be preserved
    reconstructed = " ".join(result).replace("  ", " ")
    assert "word1" in reconstructed
    assert "word5" in reconstructed


def test_chunk_empty_text() -> None:
    """Test chunking empty text"""
    result = chunk_on_delimiter("", delimiter=" ", max_length=100)
    assert result == []


def test_chunk_single_word() -> None:
    """Test chunking single word"""
    result = chunk_on_delimiter("hello", delimiter=" ", max_length=100)
    assert result == ["hello"]


def test_chunk_word_longer_than_max_length() -> None:
    """Test handling word longer than max_length"""
    long_word = "verylongwordthatexceedsmaxlength"
    result = chunk_on_delimiter(long_word, delimiter=" ", max_length=10)

    # Should split the long word
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= 10

    # Reconstructed text should contain all characters
    reconstructed = "".join(result)
    assert reconstructed == long_word


def test_chunk_with_different_delimiter() -> None:
    """Test chunking with different delimiter"""
    text = "item1,item2,item3,item4"
    result = chunk_on_delimiter(text, delimiter=",", max_length=15)

    for chunk in result:
        assert len(chunk) <= 15

    # Should preserve items
    reconstructed = ",".join(result)
    assert "item1" in reconstructed
    assert "item4" in reconstructed


def test_chunk_max_length_validation() -> None:
    """Test max_length validation"""
    with pytest.raises(ValueError, match="max_length must be at least 1"):
        chunk_on_delimiter("test", max_length=0)

    with pytest.raises(ValueError, match="max_length must be at least 1"):
        chunk_on_delimiter("test", max_length=-1)


def test_chunk_preserves_content() -> None:
    """Test that chunking preserves all content"""
    text = "The quick brown fox jumps over the lazy dog"
    result = chunk_on_delimiter(text, delimiter=" ", max_length=20)

    # Join all chunks and normalize spaces
    reconstructed = " ".join(result).strip()
    # Remove extra spaces that might be introduced
    reconstructed = " ".join(reconstructed.split())

    assert reconstructed == text


def test_chunk_respects_max_length() -> None:
    """Test that chunks respect max_length"""
    text = "a " * 100  # 200 characters
    max_len = 50
    result = chunk_on_delimiter(text, delimiter=" ", max_length=max_len)

    for chunk in result:
        assert len(chunk) <= max_len


def test_chunk_edge_case_exact_length() -> None:
    """Test edge case where text exactly fits max_length"""
    text = "exact"  # 5 characters
    result = chunk_on_delimiter(text, delimiter=" ", max_length=5)
    assert result == ["exact"]


def test_chunk_multiple_spaces_delimiter() -> None:
    """Test with multi-character delimiter"""
    text = "item1::item2::item3::item4"
    result = chunk_on_delimiter(text, delimiter="::", max_length=15)

    for chunk in result:
        assert len(chunk) <= 15

    # Should handle the delimiter correctly
    reconstructed = "::".join(result)
    assert "item1" in reconstructed
