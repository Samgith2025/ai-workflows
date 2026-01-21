#!/usr/bin/env python3
"""Extract full video data from Sora page including all encodings."""

import asyncio
import sys
import json
import re
from urllib.parse import unquote
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230"

    print(f"Extracting from: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Get page HTML and search for encodings
        html = await page.content()

        # Decode unicode escapes in the HTML
        html_decoded = html.encode().decode('unicode_escape', errors='ignore')

        # Find all video URLs
        print("=== All video URLs in page ===\n")

        # Pattern for Azure video URLs
        video_pattern = r'https://videos\.openai\.com/az/files/[^"\\]+(?:\\u0026[^"\\]+)*'
        matches = re.findall(video_pattern, html)

        unique_urls = set()
        for match in matches:
            # Decode unicode escapes
            decoded = match.replace('\\u0026', '&')
            unique_urls.add(decoded)

        for i, video_url in enumerate(sorted(unique_urls, key=len)):
            # Identify the type based on URL path
            url_type = "unknown"
            if "/drvs/md/" in video_url:
                url_type = "MEDIUM (md) - watermarked display"
            elif "/drvs/thumbnail/" in video_url:
                url_type = "THUMBNAIL"
            elif "/raw" in video_url and "/drvs/" not in video_url:
                url_type = "SOURCE (raw) - possibly unwatermarked"

            print(f"{i+1}. [{url_type}]")
            print(f"   {video_url[:120]}...")
            print()

        # Check specifically for source vs source_wm
        print("\n=== Encodings analysis ===\n")

        source_match = re.search(r'"source":\s*\{\s*"path"\s*:\s*"([^"]+)"', html)
        source_wm_match = re.search(r'"source_wm":\s*\{\s*"path"\s*:\s*"([^"]+)"', html)

        if source_match:
            source_url = source_match.group(1).replace('\\u0026', '&')
            print(f"source (potential unwatermarked):")
            print(f"  {source_url[:100]}...")
            print()

        if source_wm_match:
            source_wm_url = source_wm_match.group(1).replace('\\u0026', '&')
            print(f"source_wm (watermarked):")
            print(f"  {source_wm_url[:100]}...")
            print()

        if source_match and source_wm_match:
            if source_match.group(1) == source_wm_match.group(1):
                print("WARNING: source and source_wm have SAME URL")
                print("This means the public share only exposes the watermarked version.")
            else:
                print("GOOD: source and source_wm have DIFFERENT URLs!")
                print("The 'source' URL may be unwatermarked.")

        # Current video element
        video_src = await page.evaluate("() => document.querySelector('video')?.src")
        if video_src:
            print(f"\nCurrently playing in video element:")
            print(f"  {video_src[:100]}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
