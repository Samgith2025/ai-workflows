# Sora Video Extraction

Extract MP4 files from Sora share links and download them for processing.

## Quick Start

### Option 1: Simple CLI (Easiest for One-Off Usage)

```bash
cd /Users/samson/tiktok/ai-workflows

# Download to temp directory
python scripts/extract_sora.py "https://sora.chatgpt.com/share/xxxx"

# Download to specific location
python scripts/extract_sora.py "https://sora.chatgpt.com/share/xxxx" "./videos/my-video.mp4"
```

Output:
```
✓ Download complete: /tmp/sora_videos/video.mp4
  Size: 42.50 MB
```

### Option 2: Temporal Workflow (For Automated Pipelines)

Start a workflow to download a video:

```python
import asyncio
import uuid
from temporalio.client import Client
from app.temporal.workflows.sora_download import SoraDownloadWorkflow
from app.temporal.schemas import SoraExtractionInput

async def download_video():
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        SoraDownloadWorkflow.run,
        SoraExtractionInput(
            share_url="https://sora.chatgpt.com/share/xxxx"
        ),
        id=f"sora-download-{uuid.uuid4()}",
        task_queue="default",
    )

    result = await handle.result()
    print(f"Video saved to: {result.local_path}")
    print(f"File size: {result.file_size_bytes / (1024*1024):.2f} MB")

asyncio.run(download_video())
```

### Option 3: Use in Your Own Workflow

Include the extraction activity in any workflow:

```python
from temporalio import workflow
from app.temporal.activities.sora_extraction import extract_sora_video
from app.temporal.schemas import SoraExtractionInput, SoraExtractionOutput

@workflow.defn
class MyCustomWorkflow:
    @workflow.run
    async def run(self, sora_url: str) -> str:
        # Extract video from Sora
        result: SoraExtractionOutput = await workflow.execute_activity(
            extract_sora_video,
            SoraExtractionInput(share_url=sora_url),
            start_to_close_timeout=600,
        )

        # Do something with result.local_path
        return result.local_path
```

## How It Works

### Step 1: Inspect Share Page
- HTTP GET request to the Sora share URL
- Parse HTML to find `<video>` tags, `<source>` elements, or `<meta>` tags
- Extract the direct CDN MP4 URL

### Step 2: Resolve MP4 URL
- Look for patterns like `https://video-cdn.openai.com/...mp4`
- Follow redirects if needed
- Return the final `.mp4` URL

### Step 3: Download Video
- Stream the MP4 from CDN to local storage
- Chunk-based download (10 MB chunks) for memory efficiency
- Show progress as it downloads

## API Reference

### SoraExtractionService

Main service class (all methods are async):

```python
from app.core.services.sora_extraction.service import SoraExtractionService

async with SoraExtractionService() as service:
    # Extract and download to temp directory
    path = await service.extract_and_download(
        sora_share_url="https://sora.chatgpt.com/share/xxxx"
    )

    # Or specify output path
    path = await service.extract_and_download(
        sora_share_url="https://sora.chatgpt.com/share/xxxx",
        output_path=Path("./my_video.mp4")
    )
```

### SoraClient

Low-level client for URL extraction only (doesn't download):

```python
from app.core.services.sora_extraction.client import SoraClient

async with SoraClient() as client:
    mp4_url = await client.get_mp4_url("https://sora.chatgpt.com/share/xxxx")
    print(f"MP4 URL: {mp4_url}")
```

### VideoDownloader

Low-level downloader (for when you already have the MP4 URL):

```python
from app.core.services.sora_extraction.downloader import VideoDownloader
from pathlib import Path

async with VideoDownloader() as downloader:
    path = await downloader.download(
        url="https://video-cdn.openai.com/...mp4",
        output_path=Path("./video.mp4")
    )
```

## Default Locations

- **Temp directory**: `/tmp/sora_videos/`
- **Filename**: `video.mp4` (if no explicit path given)

## Error Handling

The service will raise:

- `ValueError`: If URL is invalid or MP4 can't be extracted
- `aiohttp.ClientError`: If HTTP requests fail
- `IOError`: If file operations fail

Example error handling:

```python
from app.core.services.sora_extraction.service import SoraExtractionService

async with SoraExtractionService() as service:
    try:
        path = await service.extract_and_download(sora_url)
    except ValueError as e:
        print(f"Invalid URL or extraction failed: {e}")
    except Exception as e:
        print(f"Network or file error: {e}")
```

## Troubleshooting

### "Could not find MP4 URL in Sora share page"
- The Sora share page HTML structure may have changed
- Check that the share URL is correct and the video is accessible
- The video might be expired or access restricted

### Large video timeout
- Downloads have a 5-minute timeout by default
- For videos > 1 GB, you may need to increase timeout in the code

### Out of disk space
- Videos download to `/tmp/sora_videos/` by default
- Ensure you have enough free space
- Specify a different `temp_dir` if needed

## Integration with Your Workflow

After downloading, you can:

1. **Upload to storage**:
```python
from app.core.services.storage import get_storage

storage = get_storage()
storage.upload_file(path, "videos/sora/")
```

2. **Process with FFmpeg**:
```python
from app.core.services.ffmpeg import get_ffmpeg_service

ffmpeg = get_ffmpeg_service()
await ffmpeg.get_info(str(path))
```

3. **Generate audio**:
```python
from app.temporal.activities.voice import generate_voice_activity

audio_path = await workflow.execute_activity(
    generate_voice_activity,
    # ...
)
```

## Architecture

```
Sora Share URL
    ↓
SoraClient.get_mp4_url()
    ├─ Fetch HTML from share page
    └─ Parse HTML/JSON for video source
    ↓
Direct CDN MP4 URL
    ↓
VideoDownloader.download()
    ├─ Stream chunks (10 MB)
    └─ Write to local storage
    ↓
Local MP4 File (/tmp/sora_videos/video.mp4)
```

## Performance

- **HTML parsing**: ~500ms
- **MP4 download**: Depends on file size and network
  - 50 MB video @ 10 Mbps: ~40 seconds
  - 100 MB video @ 10 Mbps: ~80 seconds
- **Memory**: ~10 MB (constant, regardless of video size due to chunking)

## Limits

- Max video size: Limited by disk space only
- Max download time: 5 minutes (configurable)
- File size: Stored in `SoraExtractionOutput.file_size_bytes` (int, up to 2 GB)
