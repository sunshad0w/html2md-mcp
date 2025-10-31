"""Core HTML to Markdown conversion functionality."""

import asyncio
import logging
from typing import Any, Literal
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from .cache import get_cache
from .utils import calculate_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Base exception for conversion errors."""

    pass


class FetchError(ConversionError):
    """Exception raised when fetching URL fails."""

    pass


class ParseError(ConversionError):
    """Exception raised when parsing HTML fails."""

    pass


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def fetch_html(url: str, timeout: int = 30, max_size: int = 10 * 1024 * 1024) -> str:
    """
    Fetch HTML content from URL with size limit and streaming support.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds (default: 30)
        max_size: Maximum size of content to download in bytes (default: 10MB)

    Returns:
        HTML content as string

    Raises:
        FetchError: If URL is invalid, fetching fails, or content is too large
    """
    if not validate_url(url):
        raise FetchError(f"Invalid URL format: {url}")

    try:
        logger.info(f"Fetching URL: {url} (max size: {max_size} bytes)")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HTML2MD-MCP/0.1; +https://github.com/html2md-mcp)"
        }

        # Use streaming to handle large pages efficiently
        response = requests.get(url, timeout=timeout, headers=headers, stream=True)
        response.raise_for_status()

        # Check Content-Length header if available
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_size:
            raise FetchError(
                f"Content too large: {content_length} bytes exceeds maximum of {max_size} bytes"
            )

        # Download content in chunks and check size
        content_chunks = []
        total_size = 0

        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            if chunk:
                content_chunks.append(chunk)
                total_size += len(chunk.encode("utf-8"))

                if total_size > max_size:
                    raise FetchError(f"Content too large: exceeds maximum of {max_size} bytes")

        html_content = "".join(content_chunks)
        logger.info(f"Successfully fetched {len(html_content)} bytes from {url}")
        return html_content

    except requests.exceptions.Timeout:
        raise FetchError(f"Timeout while fetching URL: {url}")
    except requests.exceptions.ConnectionError:
        raise FetchError(f"Connection error while fetching URL: {url}")
    except requests.exceptions.HTTPError as e:
        raise FetchError(f"HTTP error {e.response.status_code} while fetching URL: {url}")
    except FetchError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        raise FetchError(f"Unexpected error while fetching URL: {url} - {str(e)}")


def clean_html(html: str) -> str:
    """
    Clean HTML by removing unnecessary elements.

    Uses BeautifulSoup to remove scripts, styles, navigation,
    footers, headers, and aside elements while preserving main content,
    tables, and images.

    Args:
        html: Raw HTML content

    Returns:
        Cleaned HTML content

    Raises:
        ParseError: If HTML parsing fails
    """
    try:
        logger.info("Cleaning HTML content")
        soup = BeautifulSoup(html, "lxml")

        # Remove unwanted elements
        unwanted_tags = ["script", "style", "nav", "footer", "header", "aside"]
        for tag in unwanted_tags:
            for element in soup.find_all(tag):
                element.decompose()

        cleaned = str(soup)
        logger.info(f"HTML cleaned: {len(html)} -> {len(cleaned)} bytes")
        return cleaned

    except Exception as e:
        raise ParseError(f"Error parsing HTML: {str(e)}")


def convert_to_markdown(
    html: str, include_images: bool = True, include_tables: bool = True, include_links: bool = True
) -> str:
    """
    Convert HTML to Markdown using trafilatura.

    Args:
        html: HTML content to convert
        include_images: Whether to include images in markdown (default: True)
        include_tables: Whether to include tables in markdown (default: True)
        include_links: Whether to include links in markdown (default: True)

    Returns:
        Markdown content

    Raises:
        ParseError: If conversion fails or content is empty
    """
    try:
        logger.info("Converting HTML to Markdown")

        markdown = trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=include_tables,
            include_images=include_images,
            include_links=include_links,
            url=None,  # We don't need URL for extraction
        )

        if not markdown:
            raise ParseError("Failed to extract content from HTML - result is empty")

        logger.info(f"Successfully converted to Markdown: {len(markdown)} bytes")
        return markdown

    except Exception as e:
        raise ParseError(f"Error converting HTML to Markdown: {str(e)}")


def html_to_markdown(
    url: str,
    include_images: bool = True,
    include_tables: bool = True,
    include_links: bool = True,
    timeout: int = 30,
    max_size: int = 10 * 1024 * 1024,
    use_cache: bool = False,
    cache_ttl: int = 3600,
    fetch_method: Literal["fetch", "playwright"] = "fetch",
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium",
    headless: bool = True,
    wait_for: Literal["load", "domcontentloaded", "networkidle"] = "networkidle",
    use_user_profile: bool = False,
) -> dict[str, Any]:
    """
    Complete workflow: fetch URL, clean HTML, and convert to Markdown.

    This is the main function that combines all steps:
    1. Check cache if enabled
    2. Fetch HTML from URL (using requests or playwright)
    3. Clean HTML using BeautifulSoup
    4. Convert to Markdown using trafilatura
    5. Store in cache if enabled

    Args:
        url: URL to fetch and convert
        include_images: Whether to include images in markdown (default: True)
        include_tables: Whether to include tables in markdown (default: True)
        include_links: Whether to include links in markdown (default: True)
        timeout: Request timeout in seconds (default: 30)
        max_size: Maximum size of content to download in bytes (default: 10MB)
        use_cache: Whether to use cache for this request (default: False)
        cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
        fetch_method: Method to fetch HTML: "fetch" (fast) or "playwright" (handles JS)
        browser_type: Browser to use with playwright (chromium, firefox, webkit)
        headless: Run browser in headless mode (default: True)
        wait_for: Wait strategy for page load (default: "networkidle")
        use_user_profile: Use user's browser profile with cookies (default: False)

    Returns:
        Dictionary with 'markdown' and 'url' keys

    Raises:
        FetchError: If URL fetching fails
        ParseError: If HTML parsing or conversion fails
    """
    logger.info(f"Starting conversion workflow for URL: {url}")

    # Create cache key from URL and parameters
    if use_cache:
        cache_key = calculate_hash(f"{url}|{include_images}|{include_tables}|{include_links}")
        cache = get_cache(ttl=cache_ttl)

        # Check cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"Cache hit for URL: {url}")
            return cached_result  # type: ignore[no-any-return]

    # Step 1: Fetch HTML
    if fetch_method == "playwright":
        # Import here to avoid dependency issues if playwright not installed
        from .browser import fetch_html_playwright

        logger.info(f"Using Playwright to fetch HTML from {url}")
        html = asyncio.run(
            fetch_html_playwright(
                url=url,
                browser_type=browser_type,
                headless=headless,
                wait_for=wait_for,
                use_user_profile=use_user_profile,
                timeout=timeout,
            )
        )
    else:
        # Use standard HTTP fetch
        logger.info(f"Using standard HTTP fetch for {url}")
        html = fetch_html(url, timeout=timeout, max_size=max_size)

    # Step 2: Clean HTML
    cleaned_html = clean_html(html)

    # Step 3: Convert to Markdown
    markdown = convert_to_markdown(
        cleaned_html,
        include_images=include_images,
        include_tables=include_tables,
        include_links=include_links,
    )

    result: dict[str, Any] = {
        "url": url,
        "markdown": markdown,
        "original_size": len(html),
        "cleaned_size": len(cleaned_html),
        "markdown_size": len(markdown),
    }

    markdown_size = int(result["markdown_size"])
    original_size = int(result["original_size"])
    compression = 100 - (markdown_size / original_size * 100)

    logger.info(
        f"Conversion complete. Original: {original_size} bytes, "
        f"Cleaned: {result['cleaned_size']} bytes, "
        f"Markdown: {markdown_size} bytes "
        f"(compression: {compression:.1f}%)"
    )

    # Store in cache if enabled
    if use_cache:
        cache.set(cache_key, result)
        logger.info(f"Result stored in cache for URL: {url}")

    return result
