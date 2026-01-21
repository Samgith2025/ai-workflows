#!/usr/bin/env python3
"""Extract Sora videos WITHOUT watermark using soravdl.com.

This script uses soravdl.com to download Sora videos without watermark.
It uses browser automation to handle the CSRF tokens properly.

Usage:
    python scripts/extract_sora_v2.py <sora_share_url> [output_filename]

Examples:
    # Download video (unwatermarked via soravdl)
    python scripts/extract_sora_v2.py "https://sora.chatgpt.com/p/s_xxxx"

    # With custom filename
    python scripts/extract_sora_v2.py "https://sora.chatgpt.com/p/s_xxxx" "my_video.mp4"

All videos are saved to: ~/tiktok/projects/sora-downloads/raw/
"""

import asyncio
import sys
from pathlib import Path
import re
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright

# Default download folder
DOWNLOAD_FOLDER = Path.home() / "tiktok" / "projects" / "sora-downloads" / "raw"

# soravdl.com endpoints
SORAVDL_BASE = "https://soravdl.com"
SORAVDL_PROXY = "https://soravdl.com/api/proxy/video"


def extract_video_id(url: str) -> str:
    """Extract video ID from Sora URL."""
    match = re.search(r'(s_[a-f0-9]+|gen_[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return "video"


async def get_video_info_via_browser(sora_url: str) -> dict | None:
    """Get video info from soravdl using browser automation."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        result = None

        async def capture_response(response):
            nonlocal result
            if '/download' in response.url and response.status == 200:
                try:
                    data = await response.json()
                    if data.get('success'):
                        result = data
                except:
                    pass

        page.on('response', capture_response)

        # Load soravdl
        await page.goto(SORAVDL_BASE, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        # Fill in URL and submit
        input_elem = await page.query_selector('input[type="text"], input[type="url"]')
        if input_elem:
            await input_elem.fill(sora_url)

        btn = await page.query_selector('button:has-text("Download")')
        if btn:
            await btn.click()
            await page.wait_for_timeout(5000)

        await browser.close()
        return result


async def download_video(video_id: str, output_path: Path) -> Path:
    """Download video from soravdl proxy."""
    url = f"{SORAVDL_PROXY}/{video_id}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://soravdl.com/',
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=120) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: HTTP {resp.status}")

            total = int(resp.headers.get('content-length', 0))
            downloaded = 0

            with open(output_path, 'wb') as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = (downloaded / total) * 100
                        print(f"\r   Downloading: {pct:.1f}% ({downloaded / 1024 / 1024:.1f} MB)", end='')

            print()
            return output_path


async def main():
    """Extract and download Sora video using soravdl (no watermark)."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    sora_url = sys.argv[1]
    video_id = extract_video_id(sora_url)

    DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 2:
        filename = sys.argv[2]
        if not filename.endswith('.mp4'):
            filename += '.mp4'
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sora_{video_id}_{timestamp}_nowm.mp4"

    output_path = DOWNLOAD_FOLDER / filename

    print("\n" + "="*60)
    print("SORA VIDEO EXTRACTION (NO WATERMARK)")
    print("="*60)
    print(f"\nURL: {sora_url}")
    print(f"Video ID: {video_id}")
    print(f"Output: {output_path}\n")

    # Try direct proxy download first (faster, no browser needed)
    print("1. Downloading via soravdl.com proxy...")
    try:
        await download_video(video_id, output_path)
        size_mb = output_path.stat().st_size / (1024 * 1024)

        if size_mb > 0.1:  # Got a real video
            print(f'\n{"="*60}')
            print('DOWNLOAD COMPLETE - NO WATERMARK!')
            print('='*60)
            print(f'Path: {output_path}')
            print(f'Size: {size_mb:.2f} MB\n')
            return
    except Exception as e:
        print(f"   Direct download failed: {e}")

    # Fallback: use browser to trigger soravdl
    print("\n2. Trying browser-based method...")
    info = await get_video_info_via_browser(sora_url)

    if info:
        print(f"   Source: {info.get('source', 'N/A')}")

        print("\n3. Downloading video...")
        try:
            await download_video(video_id, output_path)

            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f'\n{"="*60}')
            print('DOWNLOAD COMPLETE - NO WATERMARK!')
            print('='*60)
            print(f'Path: {output_path}')
            print(f'Size: {size_mb:.2f} MB\n')

        except Exception as e:
            print(f"\n   Download failed: {e}")
            sys.exit(1)
    else:
        print("   Failed. Video may not be accessible.")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
