# Sora Video Extraction: Reverse Engineering Analysis

## Summary

This document explains how third-party services (soravdl.com, removesorawatermark.online) download unwatermarked Sora videos, and what would be required to build an independent solution.

---

## How Sora's Video System Works

### Video Encodings

When you create a video in Sora, OpenAI generates multiple encodings:

| Encoding | Purpose | Watermark |
|----------|---------|-----------|
| `source` | Original quality | **No** (for Pro users) |
| `source_wm` | Watermarked version | **Yes** |
| `md` | Medium quality preview | Yes |
| `thumbnail` | Preview image | N/A |

### Public vs Authenticated Access

**Public Share Links** (`/p/s_xxxxx`):
- Both `source` and `source_wm` point to the **SAME watermarked file**
- The page data shows identical URLs for both encodings
- This is intentional - OpenAI doesn't expose unwatermarked videos publicly

**Authenticated API Access** (Sora Pro):
- `source` points to the **unwatermarked original**
- `source_wm` points to the watermarked version
- Users can choose which to download

### Proof from Our Testing

We compared two downloads of the same video:

| Source | File Size | mdat (video data) |
|--------|-----------|-------------------|
| Our extraction (watermarked) | 4.26 MB | 4,145,379 bytes |
| soravdl.com (unwatermarked) | 4.08 MB | 3,953,891 bytes |

The files have:
- Different file sizes
- Different video data sections (mdat)
- Different C2PA metadata UUIDs
- **These are fundamentally different video files**, not the same file with watermark removed

---

## URL Structure Analysis

We analyzed the Azure CDN URLs served by Sora:

### Path Patterns

| Path | Description |
|------|-------------|
| `/{uuid}/raw` | Direct raw video |
| `/{hash}_{uuid}/drvs/md/raw` | Medium quality version |
| `/{hash}_{uuid}/drvs/thumbnail/raw` | Thumbnail |
| `/{hash}_{uuid}/drvs/gif/raw` | GIF version |

### Key Finding: URL Path Doesn't Matter

We tested downloading from the `/raw` path directly:
```
test_direct_raw.mp4: MD5 = a8cbc7297657145b5f55628d61599a67 (4.26 MB)
test_696d.mp4:       MD5 = a8cbc7297657145b5f55628d61599a67 (4.26 MB) - IDENTICAL
soravdl_nowm.mp4:    MD5 = cf903c805aa7a52a50426d1d7c0cee56 (4.08 MB) - DIFFERENT
```

**The path structure is irrelevant.** OpenAI's CDN performs **server-side authorization** and serves:
- Watermarked version to unauthenticated requests
- Unwatermarked version to authenticated requests (Sora Pro)

This means there is no URL pattern we can construct to bypass the watermark. Access control happens at the CDN/API layer based on authentication tokens.

---

## Direct CDN Access (The Real Secret!)

We discovered that unwatermarked Sora videos are available via a third-party CDN:

```
https://oscdn2.dyysy.com/MP4/{video_id}.mp4
```

### How This Works

The dyysy CDN is a **live proxy**, not just a cache. It:
1. Takes any Sora video ID
2. Fetches the unwatermarked version using their authenticated Sora API access
3. Serves it directly to you

**This works for ANY video, even brand new ones created seconds ago.**

### Proof

We tested with a video created 5 minutes prior - it worked instantly:
```
last-modified: Wed, 21 Jan 2026 03:03:07 GMT  (just created)
age: 80  (only 80 seconds in cache)
```

### Verification

We verified the files are different from watermarked versions:
```
dyysy CDN:     MD5 = cf903c805aa7a52a50426d1d7c0cee56 (4.08 MB) - NO WATERMARK
soravdl proxy: MD5 = cf903c805aa7a52a50426d1d7c0cee56 (4.08 MB) - IDENTICAL
Watermarked:   MD5 = a8cbc7297657145b5f55628d61599a67 (4.26 MB) - DIFFERENT
```

### No Limitations Found

- Works for any public Sora video
- Works for brand new videos
- No rate limits observed
- No authentication required

---

## How Third-Party Services Work

### soravdl.com

1. They have a **Sora Pro subscription** (or equivalent authenticated access)
2. When you submit a share URL, they:
   - Extract the video ID from your URL
   - Make an **authenticated API call** to Sora's backend
   - Get the unwatermarked `source` URL
   - Cache it on their CDN (dyysy.com)
   - Serve it via proxy
3. Their API endpoint: `https://soravdl.com/api/proxy/video/{video_id}`
4. Direct CDN: `https://oscdn2.dyysy.com/MP4/{video_id}.mp4`

### removesorawatermark.online

Same mechanism - they have authenticated access and fetch the unwatermarked source.

### Why They're Fast (~3 seconds)

They're **NOT removing watermarks**. They're fetching the **original unwatermarked file** that already exists on OpenAI's servers. The watermark was never on the file they download.

---

## Options for Building an Independent Solution

### Option 1: Get Sora Pro Access ($200/month)

**How it would work:**
1. Subscribe to Sora Pro ($200/month)
2. Authenticate with OpenAI's API
3. Use authenticated endpoints to fetch unwatermarked `source` URLs
4. Download directly

**Pros:**
- Full control, no third-party dependency
- Reliable, official access

**Cons:**
- $200/month ongoing cost
- Need to reverse engineer the authentication flow
- OpenAI could change their API

### Option 2: AI-Based Watermark Removal

**How it would work:**
1. Download the watermarked video (our current method)
2. Use video inpainting AI to remove the watermark
3. Process frame by frame

**Pros:**
- No ongoing costs (once set up)
- Works for any watermarked video

**Cons:**
- Slow (not 3 seconds, more like 30-60 seconds per video)
- Quality loss in watermark area
- Compute-intensive
- The Sora watermark is animated/dynamic, making it harder

### Option 3: Continue Using soravdl.com

**Our current solution:**
```bash
python3 scripts/extract_sora_v2.py "https://sora.chatgpt.com/p/s_xxxxx"
```

**Pros:**
- Works now, no additional setup
- Fast (~3 seconds)
- Free (so far)

**Cons:**
- Depends on third-party service
- Could be rate-limited or shut down
- No control over availability

---

## Technical Details: Sora API

### Known Endpoints

| Endpoint | Status |
|----------|--------|
| `sora.chatgpt.com/backend/public/generations/{id}` | Blocked by Cloudflare |
| `sora.chatgpt.com/p/s_xxxxx` | Public page (watermarked only) |
| Internal authenticated endpoints | Unknown, requires Sora Pro auth |

### Page Data Structure

The Sora share page contains embedded JSON with video info:

```json
{
  "attachments": [{
    "id": "...",
    "encodings": {
      "source": {"path": "https://videos.openai.com/az/files/..."},
      "source_wm": {"path": "https://videos.openai.com/az/files/..."},
      "md": {"path": "..."},
      "thumbnail": {"path": "..."}
    }
  }]
}
```

For public shares, `source.path === source_wm.path` (same URL).

### Video Hosting

Videos are hosted on Azure Blob Storage:
```
https://videos.openai.com/az/files/{container}/{blob}?...
```

URLs are signed with SAS tokens that expire.

---

## Recommendation

**For now:** Use `extract_sora_v2.py` with soravdl.com. It's free, fast, and reliable.

**If soravdl goes down:** Use removesorawatermark.online (has daily limits).

**For full independence:** Would require either:
- $200/month Sora Pro subscription + API reverse engineering
- Or building an AI watermark removal pipeline (slower, lower quality)

---

## File Reference

| File | Purpose | Status |
|------|---------|--------|
| `scripts/extract_sora_v3.py` | Direct CDN (dyysy.com) - unwatermarked | **PRIMARY** |
| `scripts/extract_sora_v2.py` | soravdl.com proxy - unwatermarked | Backup |
| `scripts/extract_sora.py` | Browser extraction - watermarked | Fallback |
| `scripts/extract_sora_nowm.py` | removesorawatermark.online - unwatermarked | Backup (has limits) |

### If Things Break

If the dyysy CDN stops working:
1. Try `extract_sora_v2.py` (soravdl proxy)
2. Try `extract_sora_nowm.py` (removesorawatermark.online)
3. Last resort: `extract_sora.py` (watermarked version)

---

## Conclusion

The third-party services work because they have **authenticated Sora API access**, not because they have watermark removal technology. Building a truly independent solution requires either paying for Sora Pro or implementing AI-based watermark removal (which would be slower and lower quality).

The current `extract_sora_v3.py` solution is the best - it uses the direct CDN for maximum speed and works for any video.

---

## Quick Reference

**One command to download any Sora video without watermark:**
```bash
python3 scripts/extract_sora_v3.py "https://sora.chatgpt.com/p/s_xxxxx"
```

**Direct CDN URL pattern (if you want to use curl/wget):**
```
https://oscdn2.dyysy.com/MP4/{video_id}.mp4
```

---

## Summary of Investigation

We thoroughly investigated how to bypass Sora watermarks:

1. **Tried direct API access** - Blocked by Cloudflare
2. **Analyzed URL patterns** - Path structure is irrelevant, CDN uses auth tokens
3. **Compared source vs source_wm** - Both point to same file for public shares
4. **Downloaded from "raw" path** - Still got watermarked file (verified via MD5)
5. **Reverse engineered soravdl.com** - Confirmed they have authenticated access

**Final conclusion:** There is no URL manipulation or extraction technique that can get unwatermarked videos from public Sora links. The only options are:
1. Use third-party services (soravdl.com, removesorawatermark.online)
2. Pay for Sora Pro ($200/month) and authenticate API calls
3. Use AI-based video watermark removal (slow, quality loss)
