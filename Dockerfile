# Use Python 3.11 slim image
FROM python:3.11-slim

# Metadata labels
LABEL org.opencontainers.image.title="HTML to Markdown MCP Server"
LABEL org.opencontainers.image.description="MCP server for converting HTML webpages to clean Markdown format. Reduces HTML size by 90-95% while preserving tables, images, and links."
LABEL org.opencontainers.image.authors="sunshad0w"
LABEL org.opencontainers.image.url="https://github.com/sunshad0w/html2md-mcp"
LABEL org.opencontainers.image.source="https://github.com/sunshad0w/html2md-mcp"
LABEL org.opencontainers.image.version="0.3.0"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="sunshad0w"
LABEL keywords="mcp,html-to-markdown,web-scraping,claude,playwright,markdown,html-converter"

# MCP Registry label (required for MCP registry)
LABEL io.modelcontextprotocol.server.name="io.github.sunshad0w/html2md"

# Set working directory
WORKDIR /app

# Copy project files first (for better layer caching)
COPY pyproject.toml ./
COPY src/ ./src/
COPY README.md LICENSE CHANGELOG.md ./

# Install everything in a single layer for minimal image size
RUN apt-get update && \
    # Install minimal base packages (playwright --with-deps will add the rest)
    apt-get install -y --no-install-recommends wget ca-certificates && \
    # Install Python dependencies
    pip install --no-cache-dir -e . && \
    # Install Playwright with Chromium and all system dependencies
    playwright install --with-deps chromium && \
    # Aggressive cleanup to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /root/.cache/pip && \
    rm -rf /root/.cache/ms-playwright && \
    rm -rf /tmp/* && \
    # Remove unnecessary Playwright files
    find /root/.cache -type f -delete 2>/dev/null || true

# Create non-root user for security
RUN useradd -m -u 1000 mcp && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Expose MCP server port (if needed for future use)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run MCP server
CMD ["python", "-m", "html2md.server"]
