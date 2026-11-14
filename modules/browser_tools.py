"""modules/browser_tools.py
Phase 6: Browser automation via Playwright with session persistence and safety controls.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from core.config import Config
from core.tools import tool

# Check if playwright is available
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class BrowserSession:
    """Singleton session manager for interactive Playwright browser automation."""
    _playwright: Optional[Any] = None
    _browser: Optional[Any] = None
    _context: Optional[Any] = None
    _page: Optional[Any] = None

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Playwright feature is enabled in .env."""
        val = os.getenv("ENABLE_PLAYWRIGHT", "true").lower().strip()
        return val in ("true", "1", "yes")

    @classmethod
    def get_or_create_page(cls, headless: bool = False) -> Optional[Any]:
        """Ensure active browser page exists."""
        if not HAS_PLAYWRIGHT:
            return None

        if cls._page and not cls._page.is_closed():
            return cls._page

        try:
            if not cls._playwright:
                cls._playwright = sync_playwright().start()

            # Launch visible Chromium browser (user sees Jarvis working)
            if not cls._browser:
                user_data_dir = Config.PROJECT_ROOT / "memory" / "browser_profile"
                user_data_dir.mkdir(parents=True, exist_ok=True)
                cls._context = cls._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=headless,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"],
                )
                pages = cls._context.pages
                cls._page = pages[0] if pages else cls._context.new_page()
            return cls._page
        except Exception as e:
            print(f"[BrowserSession] Launch error: {e}")
            return None

    @classmethod
    def close(cls) -> str:
        """Close browser context and stop Playwright."""
        closed = False
        try:
            if cls._context:
                cls._context.close()
                cls._context = None
                cls._page = None
                closed = True
            if cls._browser:
                cls._browser.close()
                cls._browser = None
                closed = True
            if cls._playwright:
                cls._playwright.stop()
                cls._playwright = None
                closed = True
        except Exception:
            pass
        return "Browser session closed." if closed else "No active browser session was open."


# ── Browser Automation Tools ──────────────────────────────────────────────

@tool(
    name="browser_open",
    description="Launch browser and navigate to a URL using Playwright.",
    params_schema={
        "url": {
            "type": "string",
            "description": "Full URL to navigate to (e.g. 'https://github.com').",
        }
    },
    risk="low",
)
def browser_open(url: str = "https://www.google.com") -> str:
    """Open browser to URL."""
    if not BrowserSession.is_enabled():
        return "Browser automation .env mein disabled hai (ENABLE_PLAYWRIGHT=false)."
    if not HAS_PLAYWRIGHT:
        return "Playwright library install nahi hai bhai. Use 'pip install playwright' and 'playwright install chromium'."

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    page = BrowserSession.get_or_create_page()
    if not page:
        return "Browser launch karne mein dikkat aayi."

    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        title = page.title()
        return f"Browser opened: '{title}' ({url})."
    except Exception as e:
        return f"Failed to navigate to {url}: {e}"


@tool(
    name="browser_search",
    description="Search the web interactively inside the Playwright browser window.",
    params_schema={
        "query": {
            "type": "string",
            "description": "Search query terms.",
        }
    },
    risk="low",
)
def browser_search(query: str) -> str:
    """Perform Google search in the browser."""
    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable. Web search tool use karein."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "Browser launch nahi ho saka."

    try:
        search_url = f"https://www.google.com/search?q={query}"
        page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
        title = page.title()
        return f"Searched for '{query}' in browser. Current page: {title}."
    except Exception as e:
        return f"Search navigation error: {e}"


@tool(
    name="browser_click",
    description="Click an element, link, or button on the active browser page by text or CSS selector.",
    params_schema={
        "selector_or_text": {
            "type": "string",
            "description": "CSS selector or visible text of the element to click.",
        }
    },
    risk="medium",
)
def browser_click(selector_or_text: str) -> str:
    """Click element on page."""
    # Safeguard against high-risk actions
    danger_words = ["pay", "checkout", "buy now", "place order", "confirm payment", "transfer"]
    if any(w in selector_or_text.lower() for w in danger_words):
        return f"Payment ya checkout element detect hua ('{selector_or_text}'). Security ke liye direct auto-click allowed nahi hai."

    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "Koi active browser page open nahi hai."

    try:
        # Try finding by text first
        loc = page.get_by_text(selector_or_text, exact=False).first
        if loc.is_visible(timeout=2000):
            loc.click()
            return f"Clicked element with text '{selector_or_text}'."

        # Fallback to CSS selector
        page.click(selector_or_text, timeout=4000)
        return f"Clicked selector '{selector_or_text}'."
    except Exception as e:
        return f"Could not click '{selector_or_text}': {e}"


@tool(
    name="browser_type",
    description="Type text into an input field or active element in the browser.",
    params_schema={
        "text": {
            "type": "string",
            "description": "Text string to enter.",
        },
        "selector": {
            "type": "string",
            "description": "Optional CSS selector or placeholder name for the input field.",
        },
        "press_enter": {
            "type": "boolean",
            "description": "Whether to press Enter key after typing.",
        },
    },
    risk="low",
)
def browser_type(text: str, selector: Optional[str] = None, press_enter: bool = False) -> str:
    """Type into browser field."""
    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "No active browser page."

    try:
        if selector:
            page.fill(selector, text, timeout=4000)
            if press_enter:
                page.press(selector, "Enter")
            return f"Typed '{text}' into '{selector}'."
        else:
            page.keyboard.type(text)
            if press_enter:
                page.keyboard.press("Enter")
            return f"Typed '{text}' at active cursor."
    except Exception as e:
        return f"Typing error: {e}"


@tool(
    name="browser_extract_text",
    description="Extract visible readable text or article content from the active browser page.",
    params_schema={
        "selector": {
            "type": "string",
            "description": "Optional CSS selector to extract from. Defaults to 'body' or main content.",
        },
        "max_chars": {
            "type": "integer",
            "description": "Max characters to return (default 2000).",
        },
    },
    risk="low",
)
def browser_extract_text(selector: Optional[str] = None, max_chars: int = 2000) -> str:
    """Extract page text."""
    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "No active browser page open."

    try:
        target = selector or "body"
        text = page.locator(target).inner_text(timeout=5000)
        clean_text = " ".join(text.split())
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + "... [truncated]"
        return f"Page content ({page.title()}):\n{clean_text}"
    except Exception as e:
        return f"Text extraction error: {e}"


@tool(
    name="browser_screenshot",
    description="Take a screenshot of the current browser page and save it.",
    params_schema={
        "save_path": {
            "type": "string",
            "description": "Optional destination path for the screenshot image.",
        }
    },
    risk="low",
)
def browser_screenshot(save_path: Optional[str] = None) -> str:
    """Capture browser page screenshot."""
    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "No active browser page."

    try:
        out_path = Path(save_path) if save_path else Config.PROJECT_ROOT / f"browser_shot_{int(time.time())}.png"
        page.screenshot(path=str(out_path), full_page=False)
        return f"Browser screenshot saved to: {out_path.name}"
    except Exception as e:
        return f"Browser screenshot error: {e}"


@tool(
    name="browser_download",
    description="Download a file or initiate download on the current page.",
    params_schema={
        "url": {
            "type": "string",
            "description": "Direct file URL to download.",
        }
    },
    risk="low",
)
def browser_download(url: str) -> str:
    """Download a file via browser or direct request."""
    if not BrowserSession.is_enabled() or not HAS_PLAYWRIGHT:
        return "Browser automation unavailable."

    page = BrowserSession.get_or_create_page()
    if not page:
        return "No active browser page."

    try:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        with page.expect_download(timeout=15000) as download_info:
            page.goto(url)
        download = download_info.value
        suggested_name = download.suggested_filename
        target_path = downloads_dir / suggested_name
        download.save_as(str(target_path))
        return f"Downloaded '{suggested_name}' to Downloads folder."
    except Exception as e:
        return f"Download failed or timed out: {e}"


@tool(
    name="browser_close",
    description="Close the Playwright browser window and release resources.",
    params_schema={},
    risk="low",
)
def browser_close() -> str:
    """Close browser session."""
    return BrowserSession.close()
