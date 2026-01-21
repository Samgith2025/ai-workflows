# Sora Video Extraction Guide

## Overview

This guide documents how to extract and download MP4 videos from Sora share links (`https://sora.chatgpt.com/p/s_xxxx`).

**Important: Downloaded videos have the Sora watermark** unless you use an unwatermarked source (see below).

## Watermark Status

| Method | Watermark | Speed | Notes |
|--------|-----------|-------|-------|
| `extract_sora_v3.py` (direct CDN) | **No** | ~3 seconds | **RECOMMENDED** - works for any video |
| `extract_sora_v2.py` (soravdl.com) | **No** | ~5 seconds | Backup method |
| `extract_sora.py` (browser) | **Yes** | ~10 seconds | Fallback if CDN goes down |
| removesorawatermark.online | **No** | ~3 seconds | Has daily limits |
| Sora Pro subscription ($200/mo) | **No** | Direct download | Official method |

> **See also:** [SORA_EXTRACTION_REVERSE_ENGINEERING.md](SORA_EXTRACTION_REVERSE_ENGINEERING.md) for technical details on how these services work.

### Why Watermarks Exist

- Sora's public share links only expose watermarked video URLs
- The `source` and `source_wm` encodings point to the **same file** for public shares
- Unwatermarked access requires authenticated API calls with a Sora Pro account

### Getting Unwatermarked Videos

**Option 1: Use extract_sora_v3.py** (Recommended - fastest, direct CDN)
```bash
python3 scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxxx"
```
This uses a direct CDN (`oscdn2.dyysy.com`) that caches unwatermarked Sora videos. Falls back to soravdl proxy if CDN doesn't have the video.

**Option 2: Use extract_sora_v2.py** (uses soravdl.com proxy)
```bash
python3 scripts/extract_sora_v2.py "https://sora.chatgpt.com/p/s_xxxxx"
```
This uses soravdl.com's proxy API which has access to unwatermarked Sora videos.

**Option 3: Use soravdl.com website directly**
1. Go to https://soravdl.com
2. Paste your Sora share URL
3. Click "Download Without Watermark"
4. Download the result

**Option 4: Use removesorawatermark.online** (has daily limits)
1. Go to https://www.removesorawatermark.online/
2. Paste your Sora share URL
3. Click "Remove Watermark"
4. Download the result

These services work because they have authenticated access to Sora's API which returns the unwatermarked `source` encoding instead of `source_wm`.

---

## Quick Start (No Watermark - Recommended)

### Single Command Extraction

```bash
cd /Users/samson/tiktok/ai-workflows
python3 scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxxx"
```

Videos are automatically saved to: `~/tiktok/projects/sora-downloads/raw/`

Filename format: `sora_<video_id>_<timestamp>_nowm.mp4`

### Custom Filename

```bash
python3 scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxxx" "my_custom_name.mp4"
```

### Direct URL (for curl/wget)

If you just want the URL pattern:
```
https://oscdn2.dyysy.com/MP4/{video_id}.mp4
```

Example:
```bash
curl -O "https://oscdn2.dyysy.com/MP4/s_6970426327f4819187b6b084557036fd.mp4"
```

---

## Fallback: Watermarked Version

If the CDN stops working, use the browser-based extraction:

```bash
python3 scripts/extract_sora.py "https://sora.chatgpt.com/p/s_xxxxx"
```

This downloads the watermarked version directly from Sora.

---

## Prerequisites

### 1. Dependencies

Ensure these packages are installed:

```bash
pip3 install aiohttp beautifulsoup4 structlog playwright
```

### 2. Playwright Browser

Install Chromium for Playwright:

```bash
python3 -m playwright install chromium
```

### 3. Directory Structure

The download folder is automatically created, but verify it exists:

```bash
mkdir -p ~/tiktok/projects/sora-downloads/raw
```

---

## How It Works

### Technical Flow

1. **User provides Sora share URL** (e.g., `https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230?psh=...`)

2. **Playwright launches a visible Chrome browser** (non-headless mode required to bypass Cloudflare)

3. **Browser navigates to the Sora URL** and waits 8 seconds for the video player to load

4. **Script extracts the video URL** from the `<video>` element's `src` attribute
   - Videos are hosted on Azure: `https://videos.openai.com/az/files/...`

5. **Downloads the MP4** using streaming chunks to the output folder

### Why Non-Headless?

Cloudflare blocks headless browsers. Running with `headless=False` (visible browser window) bypasses this protection. The browser window will briefly appear during extraction.

---

## File Locations

| Component | Path |
|-----------|------|
| CLI Script | `/Users/samson/tiktok/ai-workflows/scripts/extract_sora.py` |
| Browser Client | `/Users/samson/tiktok/ai-workflows/app/core/services/sora_extraction/browser_client.py` |
| Download Service | `/Users/samson/tiktok/ai-workflows/app/core/services/sora_extraction/service.py` |
| Video Downloader | `/Users/samson/tiktok/ai-workflows/app/core/services/sora_extraction/downloader.py` |
| Output Folder | `~/tiktok/projects/sora-downloads/raw/` |

---

## URL Formats

The system supports these Sora URL formats:

| Type | Format | Example |
|------|--------|---------|
| Private Share | `/p/s_xxxxx` | `https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230?psh=...` |
| Public Explore | `/g/gen_xxxxx` | `https://sora.chatgpt.com/g/gen_01jj1rn6q5f6jrzb4n2hpdx1gs` |

Both formats work with the extraction script.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'playwright'"

```bash
pip3 install playwright
python3 -m playwright install chromium
```

### "Could not find MP4 URL in Sora share page"

- The video may still be processing on Sora's end
- The share link may have expired
- Try opening the URL manually in a browser to verify it works

### Browser doesn't close properly

If the browser window stays open after an error, manually close it. The script uses context managers to handle cleanup, but exceptions may leave it open.

### 403 Forbidden errors

This happens when trying headless mode. Ensure the browser client uses `headless=False`:

```python
# In browser_client.py
self.headless = False  # MUST be False to bypass Cloudflare
```

---

## Code Reference

### Main Extraction Logic (browser_client.py:50-178)

The `get_mp4_url()` method:
1. Validates the URL is from `sora.chatgpt.com`
2. Creates a browser context and page
3. Sets up network interception for MP4 URLs
4. Navigates to the share URL
5. Waits 8 seconds for video to load
6. Extracts video URL using three strategies:
   - Strategy 1: `<video>` element src attribute
   - Strategy 2: Network request interception
   - Strategy 3: JavaScript DOM search

### Download Logic (downloader.py)

Streams the video in chunks (default 10MB) with progress logging.

### CLI Entry Point (extract_sora.py)

```python
async def main():
    sora_url = sys.argv[1]

    # Auto-generate filename
    video_id = extract_video_id(sora_url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sora_{video_id}_{timestamp}.mp4"
    output_path = DOWNLOAD_FOLDER / filename

    async with SoraExtractionService(headless=False) as service:
        result_path = await service.extract_and_download(
            sora_share_url=sora_url,
            output_path=output_path,
        )
```

---

## Example Session

```
$ python3 scripts/extract_sora.py "https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230?psh=HXVzZXIt..."

🚀 Starting Sora video extraction...
   URL: https://sora.chatgpt.com/p/s_69702d541e708191961ab93b4a1b9230?psh=HXVzZXIt...
   Output: /Users/samson/tiktok/projects/sora-downloads/raw/sora_s_69702d541e708191961ab93b4a1b9230_20260120_203527.mp4

⏳ Launching browser & extracting video...

✅ Download complete!
   Path: /Users/samson/tiktok/projects/sora-downloads/raw/sora_s_69702d541e708191961ab93b4a1b9230_20260120_203527.mp4
   Size: 3.38 MB
```

---

## Notes

- **Videos downloaded have the Sora watermark** - this is the only version available via public share links
- The browser window will briefly appear during extraction - this is expected
- Typical video sizes are 3-5 MB
- The signed Azure URLs in the video src expire after some time, so download promptly after extraction
- For unwatermarked videos, use removesorawatermark.online or get a Sora Pro subscription

## Technical Details: Why Watermarks Can't Be Bypassed

OpenAI's Sora serves two video encodings:
- `source` - Original quality
- `source_wm` - Watermarked version

For **public share links** (`/p/s_xxx`), both URLs point to the **same watermarked file**.
For **authenticated users with Pro subscription**, `source` points to an unwatermarked file.

The removesorawatermark.online service works in 3 seconds because they:
1. Have a Sora Pro account
2. Make authenticated API requests with your share URL
3. Fetch the unwatermarked `source` URL
4. Return it for download

This is not "watermark removal" - it's accessing the unwatermarked original that Pro users can download.
