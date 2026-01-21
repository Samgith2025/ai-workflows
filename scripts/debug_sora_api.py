#!/usr/bin/env python3
"""Debug script to check Sora API response via browser."""

import asyncio
import sys
import json
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230"

    # Extract video ID
    if "s_" in url:
        video_id = url.split("s_")[1].split("?")[0]
        video_id = f"s_{video_id}"
    elif "gen_" in url:
        video_id = url.split("gen_")[1].split("?")[0]
        video_id = f"gen_{video_id}"
    else:
        print("Could not extract video ID")
        return

    api_url = f"https://sora.chatgpt.com/backend/public/generations/{video_id}"
    print(f"Video ID: {video_id}")
    print(f"API URL: {api_url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # First visit the share page to get past Cloudflare
        print("\n1. Visiting share page first to pass Cloudflare...")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        # Now try the API
        print("\n2. Fetching API endpoint...")
        response = await page.goto(api_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        content = await page.content()

        # Try to extract JSON from the page
        try:
            # The API might return raw JSON
            text = await page.inner_text("body")
            data = json.loads(text)
            print("\n3. API Response:")
            print(json.dumps(data, indent=2))

            # Check for encodings
            if "encodings" in data:
                print("\n4. Available encodings:")
                for key, value in data["encodings"].items():
                    print(f"   - {key}: {value.get('path', 'no path')[:80]}...")
        except:
            print("\n3. Could not parse JSON. Raw content:")
            print(content[:2000])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
