# Sora Extraction - Integration Examples

Real-world examples of integrating Sora video extraction into your TikTok workflow.

## Example 1: Simple Standalone Usage

**Scenario**: You generate a video in Sora, get the share link, and want to download it.

```bash
# Terminal
cd /Users/samson/tiktok/ai-workflows
python scripts/extract_sora.py "https://sora.chatgpt.com/share/abc123" \
  "projects/my-campaign/02-videos/raw/video1.mp4"
```

**Output**:
```
✓ Download complete: projects/my-campaign/02-videos/raw/video1.mp4
  Size: 42.50 MB
```

---

## Example 2: Python Script - Batch Download

**Scenario**: Download multiple Sora videos and organize them.

**File**: `batch_download_sora.py`

```python
#!/usr/bin/env python
"""Batch download videos from Sora share links."""

import asyncio
from pathlib import Path
from app.core.services.sora_extraction.service import SoraExtractionService

# Your Sora share links
SORA_VIDEOS = [
    ("https://sora.chatgpt.com/share/link1", "viral-transformation-001"),
    ("https://sora.chatgpt.com/share/link2", "trending-dance-002"),
    ("https://sora.chatgpt.com/share/link3", "motivation-quote-003"),
]

async def download_all():
    """Download all videos."""
    output_dir = Path("projects/batch-campaign/02-videos/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with SoraExtractionService() as service:
        for i, (url, name) in enumerate(SORA_VIDEOS, 1):
            print(f"\n[{i}/{len(SORA_VIDEOS)}] Downloading: {name}")

            try:
                output_path = output_dir / f"{name}.mp4"
                path = await service.extract_and_download(url, output_path=output_path)

                size_mb = path.stat().st_size / (1024*1024)
                print(f"✓ Success: {path}")
                print(f"  Size: {size_mb:.2f} MB")

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

    print("\n✓ All downloads complete!")

if __name__ == "__main__":
    asyncio.run(download_all())
```

**Run it**:
```bash
python batch_download_sora.py
```

---

## Example 3: Workflow Integration - Sora → Edit → Upload

**Scenario**: Use Temporal workflow to automate the entire process.

**File**: `app/temporal/workflows/sora_to_tiktok.py`

```python
"""Complete workflow: Sora → Edit → Upload."""

from pathlib import Path
from temporalio import workflow

from app.temporal.activities.ffmpeg import crop_to_aspect_ratio
from app.temporal.activities.sora_extraction import extract_sora_video
from app.temporal.activities.storage import upload_to_r2
from app.temporal.schemas import SoraExtractionInput


@workflow.defn
class SoraToTikTokWorkflow:
    """Download Sora video → Edit to TikTok format → Upload."""

    @workflow.run
    async def run(self, sora_url: str, campaign_name: str) -> str:
        """Execute the full pipeline.

        Args:
            sora_url: Sora share link
            campaign_name: Your campaign name

        Returns:
            URL to the final video in storage
        """
        workflow.logger.info(f"Starting Sora→TikTok workflow for {campaign_name}")

        # Step 1: Extract and download from Sora
        workflow.logger.info("Step 1: Extracting from Sora")
        extraction_result = await workflow.execute_activity(
            extract_sora_video,
            SoraExtractionInput(share_url=sora_url),
            start_to_close_timeout=600,
        )
        raw_video = extraction_result.local_path

        # Step 2: Crop to TikTok aspect ratio (9:16)
        workflow.logger.info("Step 2: Cropping to TikTok format")
        cropped_video = f"{Path(raw_video).stem}-tiktok.mp4"
        await workflow.execute_activity(
            crop_to_aspect_ratio,
            {"input": raw_video, "output": cropped_video, "aspect_ratio": "9:16"},
            start_to_close_timeout=300,
        )

        # Step 3: Upload to R2/S3
        workflow.logger.info("Step 3: Uploading to storage")
        final_url = await workflow.execute_activity(
            upload_to_r2,
            {
                "local_path": cropped_video,
                "remote_folder": f"videos/{campaign_name}/",
            },
            start_to_close_timeout=60,
        )

        workflow.logger.info(f"Workflow complete: {final_url}")
        return final_url
```

**Start the workflow**:
```python
import asyncio
import uuid
from temporalio.client import Client
from app.temporal.workflows.sora_to_tiktok import SoraToTikTokWorkflow

async def run_workflow():
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        SoraToTikTokWorkflow.run,
        args=[
            "https://sora.chatgpt.com/share/xxx123",
            "viral-transformation-campaign"
        ],
        id=f"sora-to-tiktok-{uuid.uuid4()}",
        task_queue="default",
    )

    result = await handle.result()
    print(f"Video uploaded to: {result}")

asyncio.run(run_workflow())
```

---

## Example 4: Real-World - Create 5 Videos Weekly

**Scenario**: You generate 5 videos in Sora each week. Automate downloading, processing, and tracking them.

**File**: `weekly_sora_workflow.py`

```python
"""Weekly Sora video generation workflow."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.services.sora_extraction.service import SoraExtractionService


class SoraWeeklyWorkflow:
    """Manage weekly Sora video downloads."""

    def __init__(self, campaign_dir: Path):
        self.campaign_dir = Path(campaign_dir)
        self.raw_dir = self.campaign_dir / "02-videos" / "raw"
        self.log_file = self.campaign_dir / "sora-downloads.json"

        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def load_manifest(self) -> dict:
        """Load existing download manifest."""
        if self.log_file.exists():
            return json.loads(self.log_file.read_text())
        return {"downloads": []}

    def save_manifest(self, manifest: dict):
        """Save download manifest."""
        self.log_file.write_text(json.dumps(manifest, indent=2))

    async def download_videos(self, sora_urls: list[str]) -> list[dict]:
        """Download batch of videos.

        Args:
            sora_urls: List of Sora share URLs

        Returns:
            List of download records with metadata
        """
        manifest = self.load_manifest()
        results = []

        async with SoraExtractionService() as service:
            for i, url in enumerate(sora_urls, 1):
                print(f"\n[{i}/{len(sora_urls)}] Downloading: {url}")

                try:
                    # Generate filename
                    date = datetime.now().strftime("%Y-%m-%d")
                    filename = f"sora-{date}-{i}.mp4"
                    output_path = self.raw_dir / filename

                    # Download
                    path = await service.extract_and_download(
                        url,
                        output_path=output_path
                    )

                    size_mb = path.stat().st_size / (1024*1024)

                    record = {
                        "date": date,
                        "sora_url": url,
                        "local_path": str(path),
                        "size_mb": round(size_mb, 2),
                        "status": "downloaded",
                    }

                    results.append(record)
                    manifest["downloads"].append(record)

                    print(f"✓ Downloaded: {filename} ({size_mb:.2f} MB)")

                except Exception as e:
                    print(f"✗ Error: {e}")
                    results.append({
                        "sora_url": url,
                        "status": "failed",
                        "error": str(e),
                    })

        # Save updated manifest
        self.save_manifest(manifest)
        return results


async def main():
    """Weekly workflow."""
    campaign = "viral-this-week"
    campaign_dir = Path(f"projects/{campaign}")

    # Your 5 Sora share URLs from this week
    sora_urls = [
        "https://sora.chatgpt.com/share/xxx1",
        "https://sora.chatgpt.com/share/xxx2",
        "https://sora.chatgpt.com/share/xxx3",
        "https://sora.chatgpt.com/share/xxx4",
        "https://sora.chatgpt.com/share/xxx5",
    ]

    # Download all
    workflow = SoraWeeklyWorkflow(campaign_dir)
    results = await workflow.download_videos(sora_urls)

    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    successful = [r for r in results if r.get("status") == "downloaded"]
    failed = [r for r in results if r.get("status") == "failed"]

    print(f"✓ Successful: {len(successful)}/{len(results)}")
    total_size = sum(r.get("size_mb", 0) for r in successful)
    print(f"✓ Total size: {total_size:.2f} MB")

    if failed:
        print(f"\n✗ Failed: {len(failed)}")
        for f in failed:
            print(f"  - {f['sora_url']}: {f['error']}")

    print(f"\nManifest saved to: {workflow.log_file}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run weekly**:
```bash
python weekly_sora_workflow.py
```

---

## Example 5: Integrated with FFmpeg Processing

**Scenario**: Download, add watermark, add music, upload.

```python
import asyncio
from pathlib import Path
from app.core.services.sora_extraction.service import SoraExtractionService
from app.core.services.ffmpeg import get_ffmpeg_service
from app.core.services.voice import generate_voiceover
from app.core.services.storage import get_storage

async def full_video_pipeline():
    """Complete video processing pipeline."""
    sora_url = "https://sora.chatgpt.com/share/xxx"
    campaign = "my-campaign"

    # Setup
    output_dir = Path(f"projects/{campaign}/02-videos")
    raw_dir = output_dir / "raw"
    edited_dir = output_dir / "edited"
    edited_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract from Sora
    print("Step 1: Extracting from Sora...")
    async with SoraExtractionService() as service:
        raw_video = await service.extract_and_download(
            sora_url,
            output_path=raw_dir / "raw.mp4"
        )

    # 2. Crop to TikTok dimensions
    print("Step 2: Cropping to TikTok format...")
    ffmpeg = get_ffmpeg_service()
    cropped = edited_dir / "cropped.mp4"
    await ffmpeg.crop_to_aspect_ratio(
        str(raw_video),
        str(cropped),
        aspect_ratio="9:16"
    )

    # 3. Generate voiceover
    print("Step 3: Generating voiceover...")
    voiceover_text = "Check this out! This is incredible!"
    audio = edited_dir / "voiceover.mp3"
    await generate_voiceover(voiceover_text, str(audio))

    # 4. Combine video + audio
    print("Step 4: Adding audio...")
    final_video = edited_dir / "final.mp4"
    await ffmpeg.merge_audio_video(
        str(cropped),
        str(audio),
        str(final_video)
    )

    # 5. Upload
    print("Step 5: Uploading...")
    storage = get_storage()
    final_url = await storage.upload_file(
        final_video,
        f"tiktok-ready/{campaign}/"
    )

    print(f"\n✓ Complete! Ready to upload to TikTok:")
    print(f"  {final_url}")
    print(f"  Local: {final_video}")

    return final_video

asyncio.run(full_video_pipeline())
```

---

## Quick Reference: Copy-Paste Code

### Download one video
```python
import asyncio
from app.core.services.sora_extraction.service import SoraExtractionService

async def download():
    async with SoraExtractionService() as service:
        path = await service.extract_and_download("https://sora.chatgpt.com/share/xxx")
        print(f"Downloaded to: {path}")

asyncio.run(download())
```

### Just get the MP4 URL (don't download)
```python
import asyncio
from app.core.services.sora_extraction.client import SoraClient

async def get_url():
    async with SoraClient() as client:
        url = await client.get_mp4_url("https://sora.chatgpt.com/share/xxx")
        print(f"MP4 URL: {url}")

asyncio.run(get_url())
```

### Download to specific folder
```python
from pathlib import Path

path = await service.extract_and_download(
    "https://sora.chatgpt.com/share/xxx",
    output_path=Path("projects/my-campaign/02-videos/raw/video1.mp4")
)
```

---

## Integration with Your Existing Workflow

### Your Current Manual Process
```
1. Generate video in Sora (15-30 min)
2. Download manually (2 min)
3. Save to projects folder
4. Edit in CapCut (optional, 10-20 min)
5. Upload to TikTok (5 min)
6. Log results (2 min)
```

### With Sora Extraction
```
1. Generate video in Sora (15-30 min)
2. Copy share URL
3. Run: python scripts/extract_sora.py "<URL>" "<output_path>"
4. Continue with editing/uploading
```

**Time saved**: ~2-3 minutes per video (no manual download/file management)

---

## Where to Put Your Code

**For quick scripts**:
```
ai-workflows/
└── scripts/
    ├── extract_sora.py       (already provided)
    └── my_download_script.py (your scripts here)
```

**For integration into workflows**:
```
ai-workflows/
└── app/temporal/workflows/
    ├── sora_download.py        (already provided)
    └── my_custom_workflow.py   (your workflows here)
```

**For testing**:
```
ai-workflows/
└── tests/
    ├── test_sora_extraction.py (already provided)
    └── test_my_integration.py  (your tests here)
```
