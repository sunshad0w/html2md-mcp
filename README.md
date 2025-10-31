# HTML to Markdown MCP Server

MCP (Model Context Protocol) server for converting HTML webpages to clean Markdown format. Reduces HTML size by ~90-95% while preserving tables, images, and important content - perfect for AI context.

## Features

- Converts HTML from URLs to clean Markdown
- Preserves tables, images, and links
- Removes unnecessary elements (scripts, styles, navigation, footers, headers)
- Significant size reduction (typically 90-95% compression)
- Configurable options for images, tables, and links
- Built with `trafilatura` and `BeautifulSoup4` for robust extraction
- **Stream processing** for efficient handling of large pages
- **Size limits** to prevent downloading excessively large content (1MB-50MB)
- **Optional caching** to speed up repeated conversions of the same URLs
- **🌐 Browser mode with Playwright** - Handles JavaScript-heavy sites and authenticated pages
  - Execute JavaScript (perfect for SPAs: React, Vue, Angular)
  - Use your browser profile with cookies (access authenticated pages!)
  - Support for Chrome, Firefox, WebKit
  - Configurable wait strategies for dynamic content

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or `pip`

### Install with uv (recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd html2md

# Install dependencies
uv pip install -e .

# Install Playwright browsers (required for browser mode)
playwright install chromium
```

### Install with pip

```bash
# Clone the repository
git clone <your-repo-url>
cd html2md

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Install Playwright browsers (required for browser mode)
playwright install chromium
```

### Docker Installation (Recommended for Production)

The easiest way to use html2md is with Docker:

```bash
# Build the image
docker build -t html2md .

# Or use pre-built image (when published)
docker pull your-registry/html2md:latest
```

For Claude Desktop, configure with Docker:

```json
{
  "mcpServers": {
    "html2md": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "html2md"
      ]
    }
  }
}
```

**Docker Image Features:**
- Pre-installed Playwright with Chromium
- Optimized for minimal size (~1GB)
- Non-root user for security
- Ready to use - no additional setup required

## Configuration

Add the server to your Claude Desktop configuration file:

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "html2md": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/html2md",
        "run",
        "html2md"
      ]
    }
  }
}
```

### Windows

Edit `%APPDATA%/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "html2md": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\absolute\\path\\to\\html2md",
        "run",
        "html2md"
      ]
    }
  }
}
```

### Linux

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "html2md": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/html2md",
        "run",
        "html2md"
      ]
    }
  }
}
```

## Usage

Once configured, the MCP server will be available in Claude Desktop. You can use the `html_to_markdown` tool:

### Example 1: Basic conversion

```
Convert this webpage to markdown: https://example.com/article
```

### Example 2: With options

```
Use the html_to_markdown tool with:
- url: https://example.com/docs
- include_images: false
- include_tables: true
```

### Example 3: Browser mode for JavaScript-heavy sites

```
Use the html_to_markdown tool with:
- url: https://spa-application.com
- fetch_method: playwright
- wait_for: networkidle
```

### Example 4: Access authenticated pages

```
Use the html_to_markdown tool with:
- url: https://private-site.com/dashboard
- fetch_method: playwright
- use_user_profile: true
- browser_type: chromium
```

**Note:** For `use_user_profile=true`, make sure Chrome is closed before running.

### Tool Parameters

**Basic Parameters:**
- `url` (required): URL of the webpage to convert
- `include_images` (optional, default: true): Include images in Markdown
- `include_tables` (optional, default: true): Include tables in Markdown
- `include_links` (optional, default: true): Include links in Markdown
- `timeout` (optional, default: 30): Request timeout in seconds (5-120)

**Performance Parameters:**
- `max_size` (optional, default: 10MB): Maximum size of content to download in bytes (1MB-50MB)
- `use_cache` (optional, default: false): Enable caching for faster repeated conversions
- `cache_ttl` (optional, default: 3600): Cache time-to-live in seconds (60-86400)

**Browser Mode Parameters:**
- `fetch_method` (optional, default: "fetch"): Fetch method - "fetch" (fast) or "playwright" (handles JS, auth)
- `browser_type` (optional, default: "chromium"): Browser to use - "chromium", "firefox", or "webkit"
- `headless` (optional, default: true): Run browser in headless mode
- `wait_for` (optional, default: "networkidle"): Wait strategy - "load", "domcontentloaded", or "networkidle"
- `use_user_profile` (optional, default: false): Use your browser profile with cookies (requires Chrome closed)

## Development

### Install development dependencies

```bash
uv pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Code formatting

```bash
# Format with black
black src/ tests/

# Lint with ruff
ruff check src/ tests/
```

### Type checking

```bash
mypy src/
```

## Architecture

The project consists of three main modules:

### `converter.py`
Core HTML to Markdown conversion functionality:
- `fetch_html()`: Downloads HTML from URL
- `clean_html()`: Removes unnecessary elements with BeautifulSoup
- `convert_to_markdown()`: Converts cleaned HTML to Markdown with trafilatura
- `html_to_markdown()`: Main workflow combining all steps

### `server.py`
MCP server implementation:
- Registers the `html_to_markdown` tool
- Handles tool calls and error responses
- Runs async MCP server with stdio transport

### `utils.py`
Utility functions:
- Hash calculation for caching
- Text formatting and truncation
- Domain extraction
- Filename sanitization

### `cache.py`
In-memory caching system:
- `SimpleCache` class with TTL support
- Global cache instance management
- Automatic expiration of old entries
- Hash-based cache keys for URL + parameters

### `browser.py`
Playwright browser automation:
- `fetch_html_playwright()` - Async browser-based HTML fetching
- Support for Chromium, Firefox, WebKit
- User profile integration for authenticated access
- Configurable wait strategies for dynamic content

## Troubleshooting

### Server not appearing in Claude Desktop

1. Check that the path in `claude_desktop_config.json` is absolute and correct
2. Restart Claude Desktop completely
3. Check Claude Desktop logs for errors

### Installation issues

```bash
# Verify Python version
python --version  # Should be 3.10+

# Try reinstalling dependencies
uv pip install --force-reinstall -e .
```

### Conversion errors

- **Timeout errors**: Increase the `timeout` parameter
- **Empty content**: Some websites may block automated requests or use JavaScript rendering
  - **Solution**: Use `fetch_method: playwright` to execute JavaScript
- **Parse errors**: The webpage structure may be unusual or malformed
- **Content too large**: Increase the `max_size` parameter (up to 50MB) or the page exceeds limits
- **Cache issues**: Disable caching with `use_cache: false` if you need fresh content

### Browser mode issues

- **Playwright not installed**: Run `playwright install chromium`
- **Browser launch fails**: Check that you have sufficient permissions and disk space
- **User profile error**: Make sure Chrome is completely closed before using `use_user_profile: true`
- **Page doesn't load fully**: Try different `wait_for` strategies:
  - `"load"` - fastest, waits for page load event
  - `"domcontentloaded"` - waits for DOM to be ready
  - `"networkidle"` - slowest but most reliable, waits for network to be idle
- **Authentication not working**: Ensure you're using `browser_type: chromium` and `use_user_profile: true`

## Performance

Typical conversion results:
- Original HTML: ~500KB - 2MB
- Markdown output: ~25KB - 100KB
- Compression: 90-95%
- Processing time: 2-10 seconds (depending on page size and network)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Credits

Built with:
- [MCP SDK](https://github.com/anthropics/mcp) - Model Context Protocol
- [trafilatura](https://github.com/adbar/trafilatura) - Web content extraction
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
