#!/usr/bin/env python
"""Simple CLI to extract MP4 from Sora share link.

Usage:
    python scripts/extract_sora.py <sora_share_url> [output_filename]

Examples:
    # Download with auto-generated filename
    python scripts/extract_sora.py "https://sora.chatgpt.com/p/s_xxxx"

    # Download with custom filename
    python scripts/extract_sora.py "https://sora.chatgpt.com/p/s_xxxx" "my_video.mp4"

All videos are saved to: ~/tiktok/projects/sora-downloads/raw/
"""

import asyncio
import sys
from pathlib import Path
import os
import re
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default download folder
DOWNLOAD_FOLDER = Path.home() / "tiktok" / "projects" / "sora-downloads" / "raw"


def extract_video_id(url: str) -> str:
    """Extract video ID from Sora URL for filename."""
    match = re.search(r'(s_[a-f0-9]+|gen_[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return "video"


async def main():
    """Extract and download Sora video."""
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
        # Auto-generate filename: sora_<video_id>_<timestamp>.mp4
        video_id = extract_video_id(sora_url)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sora_{video_id}_{timestamp}.mp4"

    output_path = DOWNLOAD_FOLDER / filename

    # Import here to allow running without full setup
    from app.core.services.sora_extraction.service import SoraExtractionService

    print("\n🚀 Starting Sora video extraction...")
    print(f"   URL: {sora_url}")
    print(f"   Output: {output_path}\n")

    async with SoraExtractionService(headless=False) as service:
        try:
            print("⏳ Launching browser & extracting video...")

            result_path = await service.extract_and_download(
                sora_share_url=sora_url,
                output_path=output_path,
            )

            size_mb = result_path.stat().st_size / (1024*1024)
            print(f'\n✅ Download complete!')
            print(f'   Path: {result_path}')
            print(f'   Size: {size_mb:.2f} MB\n')
        except Exception as e:
            print(f'\n❌ Error: {e}\n', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
