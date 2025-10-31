# Use Python 3.11 slim image
FROM python:3.11-slim

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
