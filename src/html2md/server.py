"""MCP Server for HTML to Markdown conversion."""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .converter import ConversionError, FetchError, ParseError, html_to_markdown
from .utils import format_bytes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("html2md")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available MCP tools.

    Returns:
        List of available tools
    """
    return [
        Tool(
            name="html_to_markdown",
            description=(
                "Convert HTML from a URL to clean Markdown format. "
                "Preserves tables, images, and links while removing unnecessary elements "
                "like scripts, styles, navigation, headers, and footers. "
                "Perfect for reducing HTML size for AI context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the webpage to convert to Markdown",
                    },
                    "include_images": {
                        "type": "boolean",
                        "description": "Whether to include images in the Markdown output",
                        "default": True,
                    },
                    "include_tables": {
                        "type": "boolean",
                        "description": "Whether to include tables in the Markdown output",
                        "default": True,
                    },
                    "include_links": {
                        "type": "boolean",
                        "description": "Whether to include links in the Markdown output",
                        "default": True,
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 120,
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "Maximum size to download in bytes (default: 10MB)",
                        "default": 10485760,
                        "minimum": 1048576,
                        "maximum": 52428800,
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Use cache for this request (reduces repeated conversions)",
                        "default": False,
                    },
                    "cache_ttl": {
                        "type": "integer",
                        "description": "Cache time-to-live in seconds (default: 3600 = 1 hour)",
                        "default": 3600,
                        "minimum": 60,
                        "maximum": 86400,
                    },
                    "fetch_method": {
                        "type": "string",
                        "enum": ["fetch", "playwright"],
                        "description": "Fetch method: fetch (fast) or playwright (JS, auth)",
                        "default": "fetch",
                    },
                    "browser_type": {
                        "type": "string",
                        "enum": ["chromium", "firefox", "webkit"],
                        "description": "Browser to use with playwright (default: chromium)",
                        "default": "chromium",
                    },
                    "headless": {
                        "type": "boolean",
                        "description": "Run browser in headless mode (default: true)",
                        "default": True,
                    },
                    "wait_for": {
                        "type": "string",
                        "enum": ["load", "domcontentloaded", "networkidle"],
                        "description": "Page load wait strategy (default: networkidle)",
                        "default": "networkidle",
                    },
                    "use_user_profile": {
                        "type": "boolean",
                        "description": "Use browser profile with cookies (requires playwright)",
                        "default": False,
                    },
                    "return_summary": {
                        "type": "boolean",
                        "description": "Return summary with metadata instead of full content (useful for large documents)",
                        "default": False,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens before auto-returning summary (default: 25000)",
                        "default": 25000,
                        "minimum": 1000,
                        "maximum": 100000,
                    },
                    "section_id": {
                        "type": "string",
                        "description": "Extract only section with this HTML anchor ID (e.g., 'PRD1480'). Mutually exclusive with section_heading.",
                    },
                    "section_heading": {
                        "type": "string",
                        "description": "Extract only section with this heading text (e.g., '7.2 Frontend'). Mutually exclusive with section_id.",
                    },
                },
                "required": ["url"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls.

    Args:
        name: Name of the tool to call
        arguments: Arguments for the tool

    Returns:
        List of text content results

    Raises:
        ValueError: If tool name is unknown
    """
    if name != "html_to_markdown":
        raise ValueError(f"Unknown tool: {name}")

    # Extract arguments with defaults
    url = arguments.get("url")
    include_images = arguments.get("include_images", True)
    include_tables = arguments.get("include_tables", True)
    include_links = arguments.get("include_links", True)
    timeout = arguments.get("timeout", 30)
    max_size = arguments.get("max_size", 10 * 1024 * 1024)
    use_cache = arguments.get("use_cache", False)
    cache_ttl = arguments.get("cache_ttl", 3600)
    fetch_method = arguments.get("fetch_method", "fetch")
    browser_type = arguments.get("browser_type", "chromium")
    headless = arguments.get("headless", True)
    wait_for = arguments.get("wait_for", "networkidle")
    use_user_profile = arguments.get("use_user_profile", False)
    return_summary = arguments.get("return_summary", False)
    max_tokens = arguments.get("max_tokens", 25000)
    section_id = arguments.get("section_id")
    section_heading = arguments.get("section_heading")

    # Validate required arguments
    if not url:
        return [TextContent(type="text", text="Error: 'url' parameter is required")]

    # Validate mutually exclusive parameters
    if section_id and section_heading:
        return [
            TextContent(
                type="text",
                text="Error: 'section_id' and 'section_heading' are mutually exclusive. Provide only one.",
            )
        ]

    try:
        logger.info(f"Processing request for URL: {url}")

        # Run the conversion in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: html_to_markdown(
                url=url,
                include_images=include_images,
                include_tables=include_tables,
                include_links=include_links,
                timeout=timeout,
                max_size=max_size,
                use_cache=use_cache,
                cache_ttl=cache_ttl,
                fetch_method=fetch_method,
                browser_type=browser_type,
                headless=headless,
                wait_for=wait_for,
                use_user_profile=use_user_profile,
                return_summary=return_summary,
                max_tokens=max_tokens,
                section_id=section_id,
                section_heading=section_heading,
            ),
        )

        # Check if result is a summary or full content
        if result.get("type") == "summary":
            # Format summary response
            import json

            stats = result["statistics"]
            toc = result.get("table_of_contents", [])
            toc_preview = "\n".join(toc[:20])
            if len(toc) > 20:
                toc_preview += f"\n... and {len(toc) - 20} more headings"

            response = f"""# Document Too Large - Summary Returned

**URL:** {url}
**Full content saved to:** `{result['saved_to']}`

## Statistics
- **Original HTML:** {stats['original_size_human']} ({stats['original_size_bytes']:,} bytes)
- **Cleaned HTML:** {stats['cleaned_size_human']} ({stats['cleaned_size_bytes']:,} bytes)
- **Markdown:** {stats['markdown_size_human']} ({stats['markdown_size_bytes']:,} bytes)
- **Estimated tokens:** {stats['estimated_tokens']:,}
- **Compression:** {stats['compression_percent']} ({stats['compression_ratio']})

## Table of Contents
{toc_preview}

## Preview (first 500 words)
{result['preview']}

---

{result['help']}
"""
        else:
            # Format full content response
            markdown = str(result["markdown"])
            original_size = int(result["original_size"])
            markdown_size = int(result["markdown_size"])
            estimated_tokens = int(result.get("estimated_tokens", 0))
            compression = 100 - (markdown_size / original_size * 100)

            section_info = ""
            if section_id or section_heading:
                section_info = f"\n**Section extracted:** {section_id if section_id else section_heading}"

            response = f"""# Conversion Successful

**URL:** {url}
**Original Size:** {format_bytes(original_size)}
**Markdown Size:** {format_bytes(markdown_size)}
**Estimated Tokens:** {estimated_tokens:,}
**Compression:** {compression:.1f}%{section_info}

---

{markdown}
"""

        logger.info(f"Successfully converted {url}")
        return [TextContent(type="text", text=response)]

    except FetchError as e:
        error_msg = f"Error fetching URL: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except ParseError as e:
        error_msg = f"Error parsing/converting content: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except ConversionError as e:
        error_msg = f"Conversion error: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.exception(error_msg)
        return [TextContent(type="text", text=error_msg)]


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting HTML to Markdown MCP Server")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def run() -> None:
    """Entry point for the server."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
