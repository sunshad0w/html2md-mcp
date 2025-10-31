"""Utility functions for HTML to Markdown converter."""

import hashlib


def calculate_hash(content: str) -> str:
    """
    Calculate SHA256 hash of content.

    Useful for caching and deduplication.

    Args:
        content: String content to hash

    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 100)
        suffix: Suffix to add when truncated (default: "...")

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_bytes(size: int) -> str:
    """
    Format bytes to human-readable format.

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 KB", "2.3 MB")
    """
    size_float = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if size_float < 1024.0:
            return f"{size_float:.1f} {unit}"
        size_float /= 1024.0
    return f"{size_float:.1f} TB"


def extract_domain(url: str) -> str | None:
    """
    Extract domain from URL.

    Args:
        url: URL to extract domain from

    Returns:
        Domain string or None if parsing fails
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return None


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing unsafe characters.

    Args:
        filename: Filename to sanitize
        max_length: Maximum length for filename (default: 255)

    Returns:
        Sanitized filename
    """
    # Remove unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")

    # Truncate if too long
    if len(filename) > max_length:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        max_name_length = max_length - len(ext) - 1
        filename = f"{name[:max_name_length]}.{ext}" if ext else name[:max_length]

    return filename
