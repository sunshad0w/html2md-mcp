"""Section extraction and summary generation for large documents."""

import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_toc(markdown: str, max_headings: int = 50) -> list[str]:
    """
    Extract table of contents from Markdown.

    Args:
        markdown: Markdown content
        max_headings: Maximum number of headings to extract (default: 50)

    Returns:
        List of heading lines (e.g., ["# Title", "## Section 1", ...])
    """
    headings = []
    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped)
            if len(headings) >= max_headings:
                break

    logger.info(f"Extracted {len(headings)} headings from Markdown")
    return headings


def extract_section_from_html(
    html: str, section_id: str | None = None, section_heading: str | None = None
) -> str:
    """
    Extract a specific section from HTML by anchor ID or heading text.

    Args:
        html: HTML content
        section_id: HTML anchor ID to find (e.g., "PRD1480")
        section_heading: Heading text to find (e.g., "7.2 Frontend")

    Returns:
        Extracted HTML section

    Raises:
        ValueError: If section not found or both/neither parameters provided
    """
    if (section_id is None and section_heading is None) or (
        section_id is not None and section_heading is not None
    ):
        raise ValueError("Must provide exactly one of: section_id or section_heading")

    soup = BeautifulSoup(html, "lxml")

    # Find the target element
    target_element = None

    if section_id:
        # Find by ID (remove # if present)
        clean_id = section_id.lstrip("#")
        target_element = soup.find(id=clean_id)
        if not target_element:
            # Try finding by name attribute
            target_element = soup.find(attrs={"name": clean_id})
        logger.info(f"Searching for section with ID: {clean_id}")
    else:
        # Find by heading text
        # Try all heading levels
        for heading_tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            headings = soup.find_all(heading_tag)
            for heading in headings:
                # Normalize text for comparison
                heading_text = heading.get_text(strip=True)
                search_text = section_heading.strip()  # type: ignore[union-attr]

                if search_text.lower() in heading_text.lower():
                    target_element = heading
                    logger.info(f"Found heading '{heading_text}' matching '{search_text}'")
                    break
            if target_element:
                break

    if not target_element:
        raise ValueError(
            f"Section not found: {section_id if section_id else section_heading}"
        )

    # Extract section content
    # Strategy: get all siblings until next heading of same or higher level
    section_elements = [target_element]

    if target_element.name and target_element.name.startswith("h"):
        # It's a heading - extract until next same-level heading
        current_level = int(target_element.name[1])
        current = target_element.next_sibling

        while current:
            if hasattr(current, "name") and current.name:
                # Check if it's a heading of same or higher level
                if current.name.startswith("h"):
                    sibling_level = int(current.name[1])
                    if sibling_level <= current_level:
                        # Stop at same or higher level heading
                        break

                section_elements.append(current)

            current = current.next_sibling
    else:
        # It's an element with ID/name - try to get its parent section
        parent = target_element.find_parent(["section", "article", "div"])
        if parent:
            section_elements = [parent]

    # Convert back to HTML
    section_html = "".join(str(elem) for elem in section_elements)

    logger.info(f"Extracted section: {len(section_html)} bytes")
    return section_html


def extract_section_from_markdown(markdown: str, section_heading: str) -> str:
    """
    Extract a specific section from Markdown by heading text.

    Args:
        markdown: Markdown content
        section_heading: Heading text to find (e.g., "7.2 Frontend" or "Frontend")

    Returns:
        Extracted Markdown section

    Raises:
        ValueError: If section not found
    """
    lines = markdown.split("\n")
    section_lines = []
    in_section = False
    section_level = None

    # Normalize search text
    search_text = section_heading.lower().strip()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this is a heading line
        if stripped.startswith("#"):
            heading_match = re.match(r"^(#+)\s+(.+)$", stripped)
            if not heading_match:
                if in_section:
                    section_lines.append(line)
                continue

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Check if this is our target section
            if not in_section and search_text in heading_text.lower():
                in_section = True
                section_level = level
                section_lines.append(line)
                logger.info(f"Found section '{heading_text}' at line {i}")
                continue

            # If we're in section and hit same/higher level heading, stop
            if in_section and section_level is not None and level <= section_level:
                break

            # If in section, keep adding lines
            if in_section:
                section_lines.append(line)
        elif in_section:
            # Keep adding content lines
            section_lines.append(line)

    if not section_lines:
        raise ValueError(f"Section not found: {section_heading}")

    result = "\n".join(section_lines)
    logger.info(f"Extracted Markdown section: {len(result)} bytes")
    return result


def estimate_tokens(text: str) -> int:
    """
    Estimate token count (rough approximation: 1 token ≈ 4 chars).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(text) // 4


def save_to_temp_file(content: str, prefix: str = "html2md_", suffix: str = ".md") -> str:
    """
    Save content to a temporary file.

    Args:
        content: Content to save
        prefix: Filename prefix (default: "html2md_")
        suffix: Filename suffix (default: ".md")

    Returns:
        Absolute path to saved file
    """
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=prefix, suffix=suffix, delete=False
    ) as f:
        f.write(content)
        filepath = f.name

    logger.info(f"Saved content to temporary file: {filepath}")
    return filepath


def generate_summary(
    markdown: str, original_size: int, cleaned_size: int, markdown_size: int, url: str
) -> dict[str, Any]:
    """
    Generate summary response for large documents.

    Args:
        markdown: Full Markdown content
        original_size: Original HTML size in bytes
        cleaned_size: Cleaned HTML size in bytes
        markdown_size: Markdown size in bytes
        url: Source URL

    Returns:
        Dictionary with summary information
    """
    # Save to temporary file
    filepath = save_to_temp_file(markdown)

    # Extract TOC
    toc = extract_toc(markdown, max_headings=50)

    # Get preview (first 500 words)
    words = markdown.split()
    preview_words = words[:500] if len(words) > 500 else words
    preview = " ".join(preview_words)
    if len(words) > 500:
        preview += "\n\n[... preview truncated ...]"

    # Calculate statistics
    tokens = estimate_tokens(markdown)
    compression = 100 - (markdown_size / original_size * 100)

    summary = {
        "type": "summary",
        "url": url,
        "saved_to": filepath,
        "statistics": {
            "original_size_bytes": original_size,
            "original_size_human": format_size(original_size),
            "cleaned_size_bytes": cleaned_size,
            "cleaned_size_human": format_size(cleaned_size),
            "markdown_size_bytes": markdown_size,
            "markdown_size_human": format_size(markdown_size),
            "estimated_tokens": tokens,
            "compression_ratio": f"{original_size / markdown_size:.2f}x",
            "compression_percent": f"{compression:.1f}%",
        },
        "preview": preview,
        "table_of_contents": toc,
        "help": (
            "This document is too large to return directly. "
            "The full content has been saved to a file. "
            "You can:\n"
            "1. Read the file using standard tools\n"
            "2. Use 'section_id' or 'section_heading' parameter to extract specific sections\n"
            "3. Review the table_of_contents to find sections of interest"
        ),
    }

    logger.info(f"Generated summary for document ({tokens} tokens, {len(toc)} headings)")
    return summary


def format_size(size_bytes: int) -> str:
    """
    Format bytes into human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "123.45 KB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"
