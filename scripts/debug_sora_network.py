#!/usr/bin/env python3
"""Debug script to intercept all network requests from Sora page."""

import asyncio
import sys
import json
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230"

    print(f"Monitoring network for: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        api_responses = []
        video_urls = []

        async def handle_response(response):
            url = response.url

            # Capture API responses
            if "/backend/" in url or "/api/" in url:
                try:
                    if response.status == 200:
                        body = await response.text()
                        api_responses.append({
                            "url": url,
                            "status": response.status,
                            "body": body[:5000]
                        })
                        print(f"[API] {url[:80]}")
                except:
                    pass

            # Capture video URLs
            if "video" in url.lower() or ".mp4" in url.lower() or "openai.com" in url.lower():
                video_urls.append(url)
                print(f"[VIDEO] {url[:100]}")

        page.on("response", handle_response)

        print("Loading page...\n")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(10000)  # Wait for all requests

        print(f"\n{'='*60}")
        print(f"Found {len(api_responses)} API responses")
        print(f"Found {len(video_urls)} video URLs")
        print(f"{'='*60}\n")

        # Print API responses
        for i, resp in enumerate(api_responses):
            print(f"\n--- API Response {i+1} ---")
            print(f"URL: {resp['url']}")
            print(f"Status: {resp['status']}")
            try:
                data = json.loads(resp['body'])
                print(f"JSON: {json.dumps(data, indent=2)[:2000]}")

                # Look for encodings
                if "encodings" in data:
                    print("\n*** ENCODINGS FOUND ***")
                    for key, value in data.get("encodings", {}).items():
                        path = value.get("path", "no path")
                        print(f"  {key}: {path[:100]}...")
            except:
                print(f"Body (not JSON): {resp['body'][:500]}")

        # Print unique video URLs
        print(f"\n--- Unique Video URLs ---")
        for url in set(video_urls):
            print(url[:150])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
