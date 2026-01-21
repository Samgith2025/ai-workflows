"""Browser-based Sora video extraction using Playwright."""

import asyncio
from typing import Optional
from urllib.parse import urlparse

import structlog
from playwright.async_api import Browser, async_playwright

logger = structlog.get_logger(__name__)


class SoraBrowserClient:
    """Extract MP4 URLs from Sora share links using browser automation."""

    def __init__(self, headless: bool = False):
        """Initialize browser client.

        Args:
            headless: Run browser in headless mode.
                      NOTE: Must be False to bypass Cloudflare protection!
        """
        self.headless = headless
        self.browser: Optional[Browser] = None

    async def __aenter__(self):
        """Context manager entry - launch browser."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        await self.close()

    async def launch(self):
        """Launch browser instance."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        logger.debug("Browser launched")

    async def close(self):
        """Close browser instance."""
        if self.browser:
            await self.browser.close()
            logger.debug("Browser closed")

    async def get_mp4_url(self, sora_share_url: str) -> str:
        """Extract MP4 URL from Sora share link using browser.

        Args:
            sora_share_url: The Sora share URL

        Returns:
            The direct MP4 URL

        Raises:
            ValueError: If the URL is invalid or MP4 cannot be extracted
            Exception: If browser operations fail
        """
        # Validate URL
        parsed = urlparse(sora_share_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {sora_share_url}")

        if "sora.chatgpt.com" not in parsed.netloc.lower():
            raise ValueError(f"URL must be from sora.chatgpt.com, got: {parsed.netloc}")

        logger.info("Extracting MP4 from Sora URL using browser", url=sora_share_url)

        if not self.browser:
            raise RuntimeError("Browser not launched. Use 'async with' or call launch()")

        # Create new page context
        context = await self.browser.new_context()
        page = await context.new_page()

        # Intercept network requests to find MP4 URLs
        mp4_urls = []

        async def handle_request(request):
            """Capture all requests including media."""
            url = request.url
            if ".mp4" in url.lower():
                logger.debug("Intercepted MP4 request", url=url)
                mp4_urls.append(url)

        async def handle_response(response):
            """Capture responses that contain MP4 URLs."""
            url = response.url

            if ".mp4" in url.lower():
                logger.debug("Found MP4 in response", url=url, status=response.status)
                if url not in mp4_urls:
                    mp4_urls.append(url)

        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            logger.debug("Navigating to Sora URL", url=sora_share_url)
            await page.goto(sora_share_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for video to load (Cloudflare + React rendering)
            logger.debug("Waiting for video player to load...")
            await page.wait_for_timeout(8000)

            # Strategy 1: Check for video element in DOM
            video_elements = await page.query_selector_all("video")
            for video_element in video_elements:
                logger.debug(f"Found video element in DOM, checking {len(video_elements)} total")

                # Try to get src from video tag - accept any video URL
                src = await video_element.get_attribute("src")
                if src and ("videos.openai.com" in src or "blob:" not in src):
                    logger.info("Extracted video from video src", url=src[:100])
                    return src

                # Try to get src from all source child elements
                sources = await video_element.query_selector_all("source")
                for source in sources:
                    src = await source.get_attribute("src")
                    if src and ("videos.openai.com" in src or "blob:" not in src):
                        logger.info("Extracted video from source tag", url=src[:100])
                        return src

            # Strategy 2: Search page content for MP4 URLs
            logger.debug(f"Found {len(mp4_urls)} MP4 URLs from network interception", count=len(mp4_urls))
            if mp4_urls:
                # Filter for actual video CDN URLs (not API responses)
                valid_urls = [url for url in mp4_urls if "video" in url.lower() or "cdn" in url.lower()]
                if valid_urls:
                    mp4_url = valid_urls[0]
                    logger.info("Extracted MP4 from network intercept", url=mp4_url)
                    return mp4_url

            # Strategy 3: Execute JavaScript to search for video URLs
            logger.debug("Trying JavaScript extraction")
            js_mp4_url = await page.evaluate("""
                () => {
                    // Try to find video src in various places
                    // 1. Direct video tags
                    const videoElems = document.querySelectorAll('video');
                    for (let v of videoElems) {
                        if (v.src && v.src.includes('.mp4')) return v.src;
                        const source = v.querySelector('source');
                        if (source && source.src && source.src.includes('.mp4')) return source.src;
                    }

                    // 2. Check all script tags for video URLs
                    const scripts = document.querySelectorAll('script');
                    for (let s of scripts) {
                        if (s.textContent) {
                            const match = s.textContent.match(/https?:[^\\s"'<>]*\\.mp4[^\\s"'<>]*/g);
                            if (match && match[0]) return match[0];
                        }
                    }

                    // 3. Check data attributes and React props
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        for (let attr of el.attributes || []) {
                            if (attr.value && attr.value.includes('.mp4')) return attr.value;
                        }
                    }

                    return null;
                }
            """)

            if js_mp4_url:
                logger.info("Extracted MP4 via JavaScript", url=js_mp4_url)
                return js_mp4_url

            logger.debug(f"All strategies failed. Found {len(mp4_urls)} network URLs, {len(video_elements)} video elements")
            raise ValueError("Could not find MP4 URL in Sora share page")

        finally:
            await context.close()


class SoraBrowserPool:
    """Reusable browser instance pool for better performance."""

    def __init__(self, pool_size: int = 1, headless: bool = True):
        """Initialize browser pool.

        Args:
            pool_size: Number of browser instances to keep alive
            headless: Run browsers in headless mode
        """
        self.pool_size = pool_size
        self.headless = headless
        self.browsers: list[Browser] = []
        self.playwright = None

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()

    async def start(self):
        """Start browser pool."""
        self.playwright = await async_playwright().start()
        for i in range(self.pool_size):
            browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            self.browsers.append(browser)
            logger.debug(f"Started browser {i+1}/{self.pool_size}")

    async def stop(self):
        """Stop all browsers in pool."""
        for browser in self.browsers:
            await browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.debug("Browser pool stopped")

    async def extract_mp4(self, sora_url: str) -> str:
        """Extract MP4 from Sora URL using a browser from the pool.

        Args:
            sora_url: Sora share URL

        Returns:
            MP4 URL
        """
        if not self.browsers:
            raise RuntimeError("Browser pool not started")

        # Use first available browser
        browser = self.browsers[0]

        # Create isolated context for this request
        context = await browser.new_context()
        page = await context.new_page()

        mp4_urls = []

        async def handle_response(response):
            if response.status == 200 and ".mp4" in response.url.lower():
                mp4_urls.append(response.url)

        page.on("response", handle_response)

        try:
            await page.goto(sora_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            # Try video element first
            video = await page.query_selector("video")
            if video:
                src = await video.get_attribute("src")
                if src and ".mp4" in src.lower():
                    return src

                source = await video.query_selector("source")
                if source:
                    src = await source.get_attribute("src")
                    if src and ".mp4" in src.lower():
                        return src

            # Use network intercept
            if mp4_urls:
                return mp4_urls[0]

            raise ValueError("Could not find MP4 URL")

        finally:
            await context.close()
