# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-10-31

### Added
- **Browser Mode Support**: Integration with Playwright for JavaScript-rendered content and authenticated pages
  - New `fetch_method` parameter: choose between "fetch" (fast) or "playwright" (JS/auth support)
  - Support for 3 browsers: Chromium, Firefox, WebKit
  - User profile integration to use browser cookies for authenticated pages (`use_user_profile`)
  - Configurable wait strategies: `load`, `domcontentloaded`, `networkidle`
  - Headless and headed browser modes
- **Performance Optimizations**:
  - Stream processing with configurable size limits (1MB-50MB, default 10MB)
  - In-memory caching with TTL support (default 1 hour)
  - New `max_size` parameter to prevent memory issues with large pages
  - New `use_cache` and `cache_ttl` parameters for caching control
- **New Module**: `browser.py` with Playwright integration
- **New Module**: `cache.py` with SimpleCache implementation
- **Enhanced Error Handling**: FetchError exceptions for browser-related issues

### Changed
- Updated `converter.py` to support dual fetch methods (fetch vs playwright)
- Updated `server.py` with 5 new tool parameters for browser mode
- Enhanced documentation in README.md with browser mode examples
- Updated CLAUDE.md with architecture details for browser integration

### Technical Details
- Added dependency: `playwright>=1.40.0`
- Full type safety with Literal types for browser_type and wait_for parameters
- Async/await support for browser operations
- Chrome user data directory detection for macOS, Windows, and Linux

### Performance
- Caching provides up to 17000x speedup for repeated conversions
- Stream processing prevents memory issues with large pages
- Browser mode tested on SPA applications (98.7% compression on Wikipedia)

## [0.1.0] - 2025-10-30

### Added
- Initial release of HTML to Markdown MCP server
- Core HTML to Markdown conversion using trafilatura and BeautifulSoup4
- MCP tool: `html_to_markdown` with parameters:
  - `url` (required): URL to convert
  - `include_images`: Include images in markdown (default: true)
  - `include_tables`: Include tables in markdown (default: true)
  - `include_links`: Include links in markdown (default: true)
  - `timeout`: Request timeout in seconds (5-120s, default: 30s)
- Three-stage conversion pipeline:
  1. HTML fetching with requests library
  2. HTML cleaning with BeautifulSoup4
  3. Markdown conversion with trafilatura
- Custom error handling with FetchError, ParseError, and ConversionError
- Compression metrics in response (original size, compressed size, ratio)
- Full type safety with mypy strict mode
- Code quality tools: black, ruff, mypy

### Features
- 90-95% size reduction for typical web pages
- Preserves tables, images, and links
- Clean output optimized for AI context windows
- Configurable timeout for slow-loading pages

### Dependencies
- mcp>=0.9.0
- trafilatura>=1.12.0
- beautifulsoup4>=4.12.0
- lxml>=5.0.0
- requests>=2.31.0
- httpx>=0.27.0

[0.2.0]: https://github.com/sunshad0w/html2md-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sunshad0w/html2md-mcp/releases/tag/v0.1.0
