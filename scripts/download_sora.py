#!/usr/bin/env python
"""Download Sora video from direct MP4 URL.

Since Sora share links are protected by Cloudflare, you need to manually get the
MP4 URL from your browser's Network tab, then use this tool to download it.

How to get the MP4 URL:
1. Open the Sora share link in your browser
2. Open DevTools (F12)
3. Go to Network tab
4. Refresh the page
5. Look for a request with a .mp4 file (usually under XHR or Media)
6. Copy the full request URL
7. Use this script to download it

Usage:
    python download_sora.py <mp4_url> [output_path]

Example:
    python download_sora.py "https://video-cdn.openai.com/...mp4" "./my_video.mp4"
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    """Download video from MP4 URL."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    mp4_url = sys.argv[1]
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    from app.core.services.sora_extraction.downloader import VideoDownloader

    print("\n🚀 Starting video download...")
    print(f"   URL: {mp4_url[:80]}...\n")

    async with VideoDownloader() as downloader:
        try:
            print("⏳ Downloading video...")

            if output_path:
                path = await downloader.download(mp4_url, output_path)
            else:
                path = await downloader.download_to_temp(mp4_url)

            size_mb = path.stat().st_size / (1024*1024)
            print(f'\n✅ Download complete!')
            print(f'   Path: {path}')
            print(f'   Size: {size_mb:.2f} MB\n')
        except Exception as e:
            print(f'\n❌ Error: {e}\n', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
