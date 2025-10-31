"""Browser-based HTML fetching using Playwright."""

import logging
import platform
from pathlib import Path
from typing import Literal

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .converter import FetchError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
BrowserType = Literal["chromium", "firefox", "webkit"]
WaitStrategy = Literal["load", "domcontentloaded", "networkidle"]


def get_chrome_user_data_dir() -> str | None:
    """
    Get Chrome user data directory path for current OS.

    Returns:
        Path to Chrome user data directory or None if not found
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        path = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    elif system == "Windows":
        path = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
    elif system == "Linux":
        path = Path.home() / ".config" / "google-chrome"
    else:
        logger.warning(f"Unknown platform: {system}")
        return None

    if path.exists():
        return str(path)

    logger.warning(f"Chrome user data directory not found: {path}")
    return None


async def fetch_html_playwright(
    url: str,
    browser_type: BrowserType = "chromium",
    headless: bool = True,
    wait_for: WaitStrategy = "networkidle",
    use_user_profile: bool = False,
    timeout: int = 30,
) -> str:
    """
    Fetch HTML content using Playwright browser.

    This function launches a real browser to fetch HTML, which enables:
    - JavaScript execution (for SPA applications)
    - Using user's browser profile (cookies, authentication)
    - Handling dynamic content

    Args:
        url: URL to fetch
        browser_type: Browser to use (chromium, firefox, webkit)
        headless: Run browser in headless mode (default: True)
        wait_for: Wait strategy for page load (default: "networkidle")
            - "load": Wait for load event
            - "domcontentloaded": Wait for DOMContentLoaded event
            - "networkidle": Wait for network to be idle (recommended for SPAs)
        use_user_profile: Use user's browser profile with cookies (default: False)
        timeout: Page load timeout in seconds (default: 30)

    Returns:
        HTML content as string

    Raises:
        FetchError: If browser launch fails, page load fails, or timeout occurs

    Example:
        >>> html = await fetch_html_playwright(
        ...     "https://example.com",
        ...     browser_type="chromium",
        ...     wait_for="networkidle"
        ... )
    """
    try:
        logger.info(
            f"Fetching URL with Playwright: {url} "
            f"(browser: {browser_type}, headless: {headless}, "
            f"wait: {wait_for}, use_profile: {use_user_profile})"
        )

        async with async_playwright() as p:
            # Select browser
            if browser_type == "chromium":
                browser_launcher = p.chromium
            elif browser_type == "firefox":
                browser_launcher = p.firefox
            elif browser_type == "webkit":
                browser_launcher = p.webkit
            else:
                raise FetchError(f"Unknown browser type: {browser_type}")

            # Launch browser with or without user profile
            browser: Browser | BrowserContext
            page: Page
            if use_user_profile and browser_type == "chromium":
                # Use Chrome user profile for accessing authenticated pages
                user_data_dir = get_chrome_user_data_dir()
                if user_data_dir is None:
                    raise FetchError(
                        "Chrome user data directory not found. "
                        "Cannot use user profile. "
                        "Try with use_user_profile=False"
                    )

                logger.info(f"Using Chrome user data directory: {user_data_dir}")

                # Note: Cannot use persistent context with headless=True in some cases
                # Launching with user data dir
                browser = await browser_launcher.launch_persistent_context(
                    user_data_dir,
                    headless=headless,
                    channel="chrome",  # Use installed Chrome
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                page = await browser.new_page()
            else:
                if use_user_profile and browser_type != "chromium":
                    logger.warning(
                        f"User profile is only supported for chromium. "
                        f"Ignoring use_user_profile for {browser_type}"
                    )

                browser = await browser_launcher.launch(headless=headless)
                context: BrowserContext = await browser.new_context()
                page = await context.new_page()

            try:
                # Navigate to URL with timeout
                logger.info(f"Navigating to {url}")
                await page.goto(url, timeout=timeout * 1000, wait_until=wait_for)  # ms

                # Get page content
                html = await page.content()
                logger.info(f"Successfully fetched {len(html)} bytes with Playwright")

                return html

            finally:
                # Always close the page and browser
                await page.close()
                await browser.close()

    except Exception as e:
        error_msg = f"Playwright error while fetching {url}: {str(e)}"
        logger.error(error_msg)
        raise FetchError(error_msg) from e
