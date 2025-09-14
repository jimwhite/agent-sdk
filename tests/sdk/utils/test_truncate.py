"""Tests for truncate utility functions."""

import tiktoken

from openhands.sdk.utils import (
    DEFAULT_TEXT_CONTENT_LIMIT,
    DEFAULT_TOKEN_LIMIT,
    DEFAULT_TRUNCATE_NOTICE,
    maybe_truncate,
    maybe_truncate_by_tokens,
)


def test_maybe_truncate_no_limit():
    """Test that maybe_truncate returns original content when no limit is set."""
    content = "This is a test string"
    result = maybe_truncate(content, truncate_after=None)
    assert result == content


def test_maybe_truncate_under_limit():
    """Test that maybe_truncate returns original content when under limit."""
    content = "Short string"
    result = maybe_truncate(content, truncate_after=100)
    assert result == content


def test_maybe_truncate_over_limit():
    """Test that maybe_truncate truncates content when over limit using head-and-tail."""  # noqa: E501
    content = "A" * 1000
    limit = 200  # Use a larger limit to accommodate the notice
    result = maybe_truncate(content, truncate_after=limit)

    # Calculate expected head and tail
    notice_len = len(DEFAULT_TRUNCATE_NOTICE)
    available_chars = limit - notice_len
    half = available_chars // 2
    head_chars = half + (available_chars % 2)
    tail_chars = half
    expected = content[:head_chars] + DEFAULT_TRUNCATE_NOTICE + content[-tail_chars:]

    assert result == expected
    assert len(result) == limit


def test_maybe_truncate_custom_notice():
    """Test that maybe_truncate uses custom truncation notice with head-and-tail."""
    content = "A" * 100
    limit = 50
    custom_notice = " [TRUNCATED]"
    result = maybe_truncate(
        content, truncate_after=limit, truncate_notice=custom_notice
    )

    # Calculate expected head and tail with custom notice
    notice_len = len(custom_notice)
    available_chars = limit - notice_len
    half = available_chars // 2
    head_chars = half + (available_chars % 2)
    tail_chars = half
    expected = content[:head_chars] + custom_notice + content[-tail_chars:]

    assert result == expected
    assert len(result) == limit


def test_maybe_truncate_exact_limit():
    """Test that maybe_truncate doesn't truncate when exactly at limit."""
    content = "A" * 50
    limit = 50
    result = maybe_truncate(content, truncate_after=limit)
    assert result == content


def test_default_limits():
    """Test that default limits are reasonable values."""
    assert DEFAULT_TEXT_CONTENT_LIMIT == 50_000
    assert DEFAULT_TOKEN_LIMIT == 12_000
    assert isinstance(DEFAULT_TRUNCATE_NOTICE, str)
    assert len(DEFAULT_TRUNCATE_NOTICE) > 0


def test_maybe_truncate_empty_string():
    """Test that maybe_truncate handles empty strings correctly."""
    result = maybe_truncate("", truncate_after=100)
    assert result == ""


def test_maybe_truncate_zero_limit():
    """Test that maybe_truncate handles zero limit correctly."""
    content = "test"
    result = maybe_truncate(content, truncate_after=0)
    # Zero limit is treated as no limit (same as None)
    assert result == content


def test_maybe_truncate_head_and_tail():
    """Test that maybe_truncate preserves head and tail content."""
    content = "BEGINNING" + "X" * 100 + "ENDING"
    limit = 50
    custom_notice = "[MIDDLE_TRUNCATED]"
    result = maybe_truncate(
        content, truncate_after=limit, truncate_notice=custom_notice
    )

    # Should preserve beginning and end
    assert result.startswith("BEGINNING")
    assert result.endswith("ENDING")
    assert custom_notice in result
    assert len(result) == limit


def test_maybe_truncate_notice_too_large():
    """Test behavior when truncation notice is larger than limit."""
    content = "A" * 100
    limit = 10
    large_notice = "X" * 20  # Larger than limit
    result = maybe_truncate(content, truncate_after=limit, truncate_notice=large_notice)

    # With simplified logic, it will still try to do head-and-tail
    # even if notice is larger than limit
    available_chars = limit - len(large_notice)  # This will be negative
    half = available_chars // 2  # This will be negative
    head_chars = half + (available_chars % 2)
    tail_chars = half
    expected = content[:head_chars] + large_notice + content[-tail_chars:]
    assert result == expected


def test_maybe_truncate_with_tokens():
    """Test that maybe_truncate works with use_tokens=True."""
    content = "word " * 100  # Create longer content to ensure truncation
    max_tokens = 50  # Use a reasonable limit that's larger than the notice
    result = maybe_truncate(content, truncate_after=max_tokens, use_tokens=True)

    # Should be truncated since it's more than max_tokens
    assert DEFAULT_TRUNCATE_NOTICE in result
    # Verify token count is within limit
    encoding = tiktoken.get_encoding("cl100k_base")
    result_tokens = len(encoding.encode(result))
    assert result_tokens <= max_tokens


def test_maybe_truncate_by_tokens_no_limit():
    """Test that maybe_truncate_by_tokens returns original content when no limit is set."""  # noqa: E501
    content = "This is a test string"
    result = maybe_truncate_by_tokens(content, max_tokens=None)
    assert result == content


def test_maybe_truncate_by_tokens_under_limit():
    """Test that maybe_truncate_by_tokens returns original content when under limit."""
    content = "Short string"
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(content))

    result = maybe_truncate_by_tokens(content, max_tokens=token_count + 10)
    assert result == content


def test_maybe_truncate_by_tokens_over_limit():
    """Test that maybe_truncate_by_tokens truncates content when over token limit."""
    # Create content with known token count
    content = "word " * 100  # Each "word " is typically 1 token
    max_tokens = 50
    result = maybe_truncate_by_tokens(content, max_tokens=max_tokens)

    # Should be truncated
    assert len(result) < len(content)
    assert DEFAULT_TRUNCATE_NOTICE in result

    # Verify token count is within limit
    encoding = tiktoken.get_encoding("cl100k_base")
    result_tokens = len(encoding.encode(result))
    assert result_tokens <= max_tokens


def test_maybe_truncate_by_tokens_custom_notice():
    """Test that maybe_truncate_by_tokens uses custom truncation notice."""
    content = "word " * 100
    max_tokens = 50
    custom_notice = " [TRUNCATED] "
    result = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, truncate_notice=custom_notice
    )

    assert custom_notice in result
    assert DEFAULT_TRUNCATE_NOTICE not in result


def test_maybe_truncate_by_tokens_exact_limit():
    """Test that maybe_truncate_by_tokens doesn't truncate when exactly at limit."""
    content = "word " * 10  # Approximately 10 tokens
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(content))

    result = maybe_truncate_by_tokens(content, max_tokens=token_count)
    assert result == content


def test_maybe_truncate_by_tokens_empty_string():
    """Test that maybe_truncate_by_tokens handles empty strings correctly."""
    result = maybe_truncate_by_tokens("", max_tokens=100)
    assert result == ""


def test_maybe_truncate_by_tokens_zero_limit():
    """Test that maybe_truncate_by_tokens handles zero limit correctly."""
    content = "test"
    result = maybe_truncate_by_tokens(content, max_tokens=0)
    # Zero limit is treated as no limit (same as None)
    assert result == content


def test_maybe_truncate_by_tokens_head_and_tail():
    """Test that maybe_truncate_by_tokens preserves head and tail content."""
    content = "BEGINNING " + "middle " * 50 + "ENDING"
    max_tokens = 20
    custom_notice = "[MIDDLE_TRUNCATED]"
    result = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, truncate_notice=custom_notice
    )

    # Should preserve beginning and end
    assert result.startswith("BEGINNING")
    assert result.endswith("ENDING")
    assert custom_notice in result


def test_maybe_truncate_by_tokens_notice_too_large():
    """Test behavior when truncation notice has more tokens than limit."""
    content = "word " * 100
    max_tokens = 5
    large_notice = " ".join(["TRUNCATED"] * 10)  # Many tokens
    result = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, truncate_notice=large_notice
    )

    # Should return just the notice when it's too large
    assert result == large_notice


def test_maybe_truncate_by_tokens_invalid_encoding():
    """Test fallback behavior with invalid encoding name."""
    content = "word " * 100
    max_tokens = 50
    result = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, encoding_name="invalid_encoding"
    )

    # Should fallback to character-based truncation
    assert len(result) < len(content)
    assert DEFAULT_TRUNCATE_NOTICE in result


def test_maybe_truncate_by_tokens_different_encodings():
    """Test that different encodings produce different results."""
    content = "word " * 100 + "This is a test with some special characters: 你好世界"
    max_tokens = 50

    result_gpt4 = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, encoding_name="cl100k_base"
    )
    result_gpt3 = maybe_truncate_by_tokens(
        content, max_tokens=max_tokens, encoding_name="p50k_base"
    )

    # Both should be truncated
    assert DEFAULT_TRUNCATE_NOTICE in result_gpt4
    assert DEFAULT_TRUNCATE_NOTICE in result_gpt3

    # Verify token counts are within limits
    encoding_gpt4 = tiktoken.get_encoding("cl100k_base")
    encoding_gpt3 = tiktoken.get_encoding("p50k_base")
    assert len(encoding_gpt4.encode(result_gpt4)) <= max_tokens
    assert len(encoding_gpt3.encode(result_gpt3)) <= max_tokens
