#!/usr/bin/env python3
"""Debug script to extract embedded data from Sora page."""

import asyncio
import sys
import json
import re
from playwright.async_api import async_playwright


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230"

    print(f"Extracting page data from: {url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)

        # Get page HTML
        html = await page.content()

        # Look for __NEXT_DATA__ (Next.js apps)
        next_data_match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if next_data_match:
            print("Found __NEXT_DATA__:")
            try:
                data = json.loads(next_data_match.group(1))
                print(json.dumps(data, indent=2)[:5000])
            except:
                print(next_data_match.group(1)[:2000])

        # Look for any script containing encodings or video URLs
        scripts = await page.query_selector_all("script")
        for i, script in enumerate(scripts):
            content = await script.inner_text()
            if content and ("encodings" in content or "source" in content.lower() and "path" in content):
                print(f"\n--- Script {i} with encodings/source ---")
                print(content[:3000])

        # Try to find video data via JavaScript
        print("\n--- Extracting via JavaScript ---")
        video_data = await page.evaluate("""
            () => {
                // Look for React fiber data
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    const keys = Object.keys(el);
                    for (let key of keys) {
                        if (key.startsWith('__reactFiber') || key.startsWith('__reactProps')) {
                            try {
                                const props = el[key];
                                const str = JSON.stringify(props);
                                if (str && str.includes('encodings')) {
                                    // Find the encodings object
                                    const match = str.match(/"encodings":\\s*({[^}]+})/);
                                    if (match) return match[0];
                                }
                            } catch (e) {}
                        }
                    }
                }

                // Search window for any video data
                for (let key of Object.keys(window)) {
                    try {
                        const str = JSON.stringify(window[key]);
                        if (str && str.includes('encodings') && str.includes('source')) {
                            return str.substring(0, 3000);
                        }
                    } catch (e) {}
                }

                return null;
            }
        """)

        if video_data:
            print("Found video data in page:")
            print(video_data)

        # Get all video sources
        print("\n--- Video elements ---")
        video_info = await page.evaluate("""
            () => {
                const videos = document.querySelectorAll('video');
                const results = [];
                for (let v of videos) {
                    results.push({
                        src: v.src,
                        currentSrc: v.currentSrc,
                        sources: Array.from(v.querySelectorAll('source')).map(s => ({
                            src: s.src,
                            type: s.type
                        }))
                    });
                }
                return results;
            }
        """)
        print(json.dumps(video_info, indent=2))

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
