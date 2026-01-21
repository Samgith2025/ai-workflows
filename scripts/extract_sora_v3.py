#!/usr/bin/env python3
"""Extract Sora videos WITHOUT watermark using direct CDN.

This script downloads Sora videos without watermark by using the dyysy CDN
which hosts unwatermarked versions of public Sora videos.

Usage:
    python scripts/extract_sora_v3.py <sora_share_url> [output_filename]

Examples:
    python scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxx"
    python scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxx" "my_video.mp4"

All videos are saved to: ~/tiktok/projects/sora-downloads/raw/
"""

import asyncio
import sys
from pathlib import Path
import re
from datetime import datetime
import aiohttp

# Default download folder
DOWNLOAD_FOLDER = Path.home() / "tiktok" / "projects" / "sora-downloads" / "raw"

# Direct CDN for unwatermarked Sora videos
DYYSY_CDN = "https://oscdn2.dyysy.com/MP4"

# Fallback: soravdl proxy
SORAVDL_PROXY = "https://soravdl.com/api/proxy/video"


def extract_video_id(url: str) -> str:
    """Extract video ID from Sora URL."""
    match = re.search(r'(s_[a-f0-9]+|gen_[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return "video"


async def download_from_cdn(video_id: str, output_path: Path) -> Path | None:
    """Try to download from dyysy CDN (fastest, direct access)."""
    url = f"{DYYSY_CDN}/{video_id}.mp4"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=60) as resp:
                if resp.status != 200:
                    return None

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

                # Verify we got a real video (not error page)
                if output_path.stat().st_size > 100000:  # > 100KB
                    return output_path
                else:
                    output_path.unlink()
                    return None

        except Exception as e:
            print(f"   CDN error: {e}")
            return None


async def download_from_soravdl(video_id: str, output_path: Path) -> Path | None:
    """Fallback: download from soravdl proxy."""
    url = f"{SORAVDL_PROXY}/{video_id}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        'Referer': 'https://soravdl.com/',
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=120) as resp:
                if resp.status != 200:
                    return None

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

                if output_path.stat().st_size > 100000:
                    return output_path
                else:
                    output_path.unlink()
                    return None

        except Exception as e:
            print(f"   Proxy error: {e}")
            return None


async def main():
    """Extract and download Sora video without watermark."""
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
    print("SORA VIDEO EXTRACTION v3 (NO WATERMARK)")
    print("="*60)
    print(f"\nURL: {sora_url}")
    print(f"Video ID: {video_id}")
    print(f"Output: {output_path}\n")

    # Method 1: Direct CDN (fastest)
    print("1. Trying direct CDN (dyysy)...")
    result = await download_from_cdn(video_id, output_path)

    if result:
        size_mb = result.stat().st_size / (1024 * 1024)
        print(f'\n{"="*60}')
        print('DOWNLOAD COMPLETE - NO WATERMARK!')
        print('='*60)
        print(f'Source: Direct CDN')
        print(f'Path: {result}')
        print(f'Size: {size_mb:.2f} MB\n')
        return

    # Method 2: soravdl proxy (fallback)
    print("\n2. Trying soravdl proxy...")
    result = await download_from_soravdl(video_id, output_path)

    if result:
        size_mb = result.stat().st_size / (1024 * 1024)
        print(f'\n{"="*60}')
        print('DOWNLOAD COMPLETE - NO WATERMARK!')
        print('='*60)
        print(f'Source: soravdl proxy')
        print(f'Path: {result}')
        print(f'Size: {size_mb:.2f} MB\n')
        return

    print("\nFailed to download. The video may not be publicly accessible.")
    sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
