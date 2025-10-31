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

    # Validate required arguments
    if not url:
        return [TextContent(type="text", text="Error: 'url' parameter is required")]

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
            ),
        )

        # Format success response
        markdown = str(result["markdown"])
        original_size = int(result["original_size"])
        markdown_size = int(result["markdown_size"])
        compression = 100 - (markdown_size / original_size * 100)

        response = f"""# Conversion Successful

**URL:** {url}
**Original Size:** {format_bytes(original_size)}
**Markdown Size:** {format_bytes(markdown_size)}
**Compression:** {compression:.1f}%

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
