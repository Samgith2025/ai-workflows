"""Helper script to debug what's on the Sora page."""

import asyncio
from playwright.async_api import async_playwright


async def debug_sora_page(url: str):
    """Load Sora page and debug what we can access."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Capture all network requests
        all_urls = []

        def on_response(response):
            all_urls.append({
                "url": response.url,
                "status": response.status,
            })

        page.on("response", on_response)

        print(f"\n🔍 Debugging Sora URL: {url}\n")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            print("✓ Page loaded (domcontentloaded)")

            # Try to wait for network to settle
            await asyncio.sleep(5)

            # Check page content
            content = await page.content()
            print(f"✓ Page content size: {len(content)} bytes")

            # Look for video tags
            videos = await page.query_selector_all("video")
            print(f"✓ Video tags found: {len(videos)}")

            # Try JavaScript extraction
            result = await page.evaluate("""
                () => {
                    const info = {
                        videos: [],
                        mp4s: [],
                        page_html_sample: document.documentElement.innerHTML.substring(0, 500)
                    };

                    // Get all videos
                    const videoElems = document.querySelectorAll('video');
                    for (let v of videoElems) {
                        info.videos.push({
                            src: v.src,
                            sources: Array.from(v.querySelectorAll('source')).map(s => ({
                                src: s.src,
                                type: s.type
                            }))
                        });
                    }

                    // Find all MP4 URLs in page
                    const bodyText = document.body.innerHTML;
                    const matches = bodyText.match(/https?:[^\\s"'<>]*\\.mp4[^\\s"'<>]*/g);
                    if (matches) info.mp4s = matches.slice(0, 5);

                    return info;
                }
            """)

            print(f"\n📹 Video Elements: {result['videos']}")
            print(f"📹 MP4 URLs found in HTML: {result['mp4s']}")

            # Print network URLs
            print(f"\n🌐 Network Requests ({len(all_urls)}):")
            video_requests = [u for u in all_urls if "video" in u["url"].lower() or ".mp4" in u["url"].lower()]
            if video_requests:
                for req in video_requests[:10]:
                    print(f"   {req['status']}: {req['url'][:80]}...")
            else:
                print("   No video-related requests found")

                print("\n   Sample of other requests:")
                for req in all_urls[:5]:
                    print(f"   {req['status']}: {req['url'][:80]}...")

        except Exception as e:
            print(f"❌ Error: {e}")

        await browser.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python browser_debugger.py <sora_url>")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(debug_sora_page(url))
