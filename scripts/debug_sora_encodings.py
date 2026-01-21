#!/usr/bin/env python3
"""Extract and compare all video encodings from Sora page."""

import asyncio
import sys
import json
import re
from urllib.parse import unquote
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230"

    print(f"Extracting encodings from: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Get page HTML
        html = await page.content()

        # Find the encodings data
        # Look for the pattern "encodings":{ ... }
        encodings_match = re.search(r'"encodings":\s*\{[^}]+\{[^}]+\}[^}]+\}', html)

        if not encodings_match:
            # Try to find in script content
            scripts = await page.query_selector_all("script")
            for script in scripts:
                content = await script.inner_text()
                if content and "encodings" in content:
                    # Extract encodings JSON
                    match = re.search(r'"encodings":\s*(\{.*?"thumbnail":\{[^}]+\}[^}]*\})', content)
                    if match:
                        encodings_match = match

        # Parse the full Next.js data
        next_data = await page.evaluate("""
            () => {
                // Search through all script content
                const scripts = document.querySelectorAll('script');
                for (let s of scripts) {
                    if (s.textContent && s.textContent.includes('encodings')) {
                        // Find attachment data
                        const match = s.textContent.match(/"attachments":\\[(\{.*?"encodings".*?\})\]/);
                        if (match) {
                            try {
                                // Clean up the JSON (handle unicode escapes)
                                let jsonStr = match[1];
                                return jsonStr;
                            } catch (e) {}
                        }
                    }
                }
                return null;
            }
        """)

        if next_data:
            print("Raw attachment data found:")
            # Clean up escaped characters
            clean_data = next_data.replace('\\u0026', '&')
            print(clean_data[:3000])
            print("\n" + "="*60 + "\n")

            # Try to extract individual URLs
            urls = {
                'source': re.search(r'"source":\{"path":"([^"]+)"', clean_data),
                'source_wm': re.search(r'"source_wm":\{"path":"([^"]+)"', clean_data),
                'md': re.search(r'"url":"([^"]+)"', clean_data),  # medium quality in url field
            }

            print("Extracted URLs:\n")
            for name, match in urls.items():
                if match:
                    decoded_url = unquote(match.group(1))
                    print(f"{name}:")
                    print(f"  {decoded_url[:150]}...")
                    print()

        # Also get video element src for comparison
        video_src = await page.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video ? video.src : null;
            }
        """)

        if video_src:
            print("\nCurrent video element src:")
            print(f"  {unquote(video_src)[:150]}...")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
