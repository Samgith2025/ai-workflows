#!/usr/bin/env python3
"""Extract Sora videos WITHOUT watermark using removesorawatermark.online API.

This script uses the removesorawatermark.online service which has a Sora Pro
subscription to fetch unwatermarked versions of Sora videos.

Usage:
    python scripts/extract_sora_nowm.py <sora_share_url> [output_filename]

Examples:
    # Download unwatermarked video
    python scripts/extract_sora_nowm.py "https://sora.chatgpt.com/p/s_xxxx"

    # With custom filename
    python scripts/extract_sora_nowm.py "https://sora.chatgpt.com/p/s_xxxx" "my_video.mp4"

Note: The service has daily limits for free users. If rate limited, the script
will fall back to downloading the watermarked version.

All videos are saved to: ~/tiktok/projects/sora-downloads/raw/
"""

import asyncio
import sys
from pathlib import Path
import re
from datetime import datetime
import aiohttp

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Default download folder
DOWNLOAD_FOLDER = Path.home() / "tiktok" / "projects" / "sora-downloads" / "raw"

# removesorawatermark.online API
REMOVER_API = "https://www.removesorawatermark.online/api/removesora/remove"


def extract_video_id(url: str) -> str:
    """Extract video ID from Sora URL for filename."""
    match = re.search(r'(s_[a-f0-9]+|gen_[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return "video"


def clean_sora_url(url: str) -> str:
    """Clean the Sora URL - remove query params as the API doesn't need them."""
    # Extract just the base URL with video ID
    match = re.search(r'(https://sora\.chatgpt\.com/[pg]/[a-zA-Z0-9_]+)', url)
    if match:
        return match.group(1)
    return url.split('?')[0]


async def try_unwatermarked_api(sora_url: str) -> dict | None:
    """Try to get unwatermarked video URL from removesorawatermark.online.

    Returns dict with video URL if successful, None if rate limited or error.
    """
    clean_url = clean_sora_url(sora_url)

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Origin': 'https://www.removesorawatermark.online',
        'Referer': 'https://www.removesorawatermark.online/',
    }

    payload = {'shareLink': clean_url}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(REMOVER_API, json=payload, headers=headers, timeout=30) as resp:
                data = await resp.json()

                if data.get('success'):
                    return data
                elif data.get('errorCode') == 'DAILY_LIMIT_REACHED':
                    print("   Daily limit reached on removesorawatermark.online")
                    return None
                else:
                    print(f"   API error: {data.get('error', 'Unknown error')}")
                    return None
        except Exception as e:
            print(f"   API request failed: {e}")
            return None


async def download_video(url: str, output_path: Path) -> Path:
    """Download video from URL to output path."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed with status {resp.status}")

            content = await resp.read()
            output_path.write_bytes(content)
            return output_path


async def main():
    """Extract and download Sora video, preferring unwatermarked version."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    sora_url = sys.argv[1]

    # Ensure download folder exists
    DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    # Generate output path
    if len(sys.argv) > 2:
        filename = sys.argv[2]
        if not filename.endswith('.mp4'):
            filename += '.mp4'
    else:
        # Auto-generate filename
        video_id = extract_video_id(sora_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sora_{video_id}_{timestamp}.mp4"

    output_path = DOWNLOAD_FOLDER / filename

    print("\n" + "="*60)
    print("SORA VIDEO EXTRACTION (Unwatermarked Preferred)")
    print("="*60)
    print(f"\nURL: {sora_url}")
    print(f"Output: {output_path}\n")

    # Try unwatermarked API first
    print("1. Trying removesorawatermark.online API...")
    result = await try_unwatermarked_api(sora_url)

    if result and result.get('success'):
        # Got unwatermarked URL!
        video_url = result.get('videoUrl') or result.get('downloadUrl')
        if video_url:
            print("   SUCCESS! Got unwatermarked video URL")
            print("\n2. Downloading unwatermarked video...")

            try:
                await download_video(video_url, output_path)
                size_mb = output_path.stat().st_size / (1024*1024)
                print(f'\n{"="*60}')
                print(f'DOWNLOAD COMPLETE (UNWATERMARKED)')
                print(f'{"="*60}')
                print(f'Path: {output_path}')
                print(f'Size: {size_mb:.2f} MB\n')
                return
            except Exception as e:
                print(f"   Download failed: {e}")
                print("   Falling back to watermarked version...")

    # Fallback to watermarked extraction
    print("\n2. Falling back to standard extraction (watermarked)...")

    from app.core.services.sora_extraction.service import SoraExtractionService

    async with SoraExtractionService(headless=False) as service:
        try:
            result_path = await service.extract_and_download(
                sora_share_url=sora_url,
                output_path=output_path,
            )

            size_mb = result_path.stat().st_size / (1024*1024)
            print(f'\n{"="*60}')
            print(f'DOWNLOAD COMPLETE (WATERMARKED)')
            print(f'{"="*60}')
            print(f'Path: {result_path}')
            print(f'Size: {size_mb:.2f} MB')
            print(f'\nNote: This version has the Sora watermark.')
            print(f'Use removesorawatermark.online manually for unwatermarked version.\n')
        except Exception as e:
            print(f'\nError: {e}\n', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
