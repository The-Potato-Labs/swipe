Twelve Labs YouTube Summary Service (Python)

Overview
- Provides a small Python service that takes a YouTube URL (or direct video URL), ingests it into Twelve Labs, waits for processing, and requests a summary.
- Uses the official Twelve Labs Python SDK (`twelvelabs` v1.x). You supply your API key via environment variable.

Files
- `service/twelvelabs_summary.py` — core service class `TwelveLabsSummarizer`.
- `service/cloudglue_summary.py` — Cloudglue integration `CloudglueSummarizer`.
- `service/cli.py` — simple CLI wrapper around the service.

Prerequisites
- Python 3.9+
- Twelve Labs API key
- Install SDK: `pip install twelvelabs`
- Optional (to avoid downloading YouTube locally): `pip install yt-dlp`
 - Optional (to resolve a direct YouTube media URL via RapidAPI): `pip install requests`

Environment
- `TWELVE_LABS_API_KEY` (required)
- `TWELVE_LABS_INDEX_ID` (optional; recommended — existing index to use)
- `TWELVE_LABS_INDEX_NAME` (optional; default: `swipe-summaries` if index must be created)
- `TWELVE_LABS_ENABLE_PEGASUS` (optional; default: `true`)
- `TWELVE_LABS_ENABLE_MARENGO` (optional; default: `false`)
- `TWELVE_LABS_LANGUAGE` (optional; default: `en`)
- `TWELVE_LABS_ORGANIZATION_ID` (optional; only if you belong to multiple orgs)
- `TWELVE_LABS_ALLOW_YT_DOWNLOAD` (optional; default: `true` — if a YouTube URL cannot be ingested by URL, download locally via `yt_dlp` and upload as a file)
 - Redis cache (YouTube → video_id mapping; analysis cache):
   - Upstash (recommended): set `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` to enable serverless REST Redis.
   - Or standard Redis: set `REDIS_URL` (e.g., `redis://:password@host:port/0`). If neither is present or unreachable, caching is disabled.
- Cloudglue:
  - `CLOUDGLUE_API_KEY` (required to use Cloudglue provider)
  - `CLOUDGLUE_BASE_URL` (optional; default `https://api.cloudglue.dev`)
  - `CLOUDGLUE_COLLECTION_ID` (optional; recommended)
  - `CLOUDGLUE_COLLECTION_NAME` (optional; default: `swipe`)
- `YT_RAPIDAPI_URL` (optional; RapidAPI endpoint that returns streaming data with `formats`/`adaptiveFormats`)
- `YT_RAPIDAPI_HOST` (optional; RapidAPI host header)
 - `YT_RAPIDAPI_KEY` (optional; RapidAPI key header)
 - `YT_DLP_COOKIES_FROM_BROWSER` (optional; browser name for yt-dlp to read cookies, e.g. `chrome`, `brave`, `edge`, `firefox`)

CLI Usage
1) Export your API key:
   `export TWELVE_LABS_API_KEY=YOUR_KEY`
2) Run the CLI:
   - YouTube: `python -m service.cli --youtube-url https://www.youtube.com/watch?v=VIDEO_ID`
   - Direct URL: `python -m service.cli --video-url https://example.com/video.mp4`
3) Optional flags:
   `--style concise` `--language en`

Programmatic Usage
```python
from service.twelvelabs_summary import TwelveLabsSummarizer
from service.cloudglue_summary import CloudglueSummarizer

summarizer = TwelveLabsSummarizer.from_env()
result = summarizer.summarize_youtube(
    youtube_url="https://www.youtube.com/watch?v=...",
    style="concise",
)
print(result["summary"])  # Full payload in result["raw"]

cg = CloudglueSummarizer.from_env()
res2 = cg.summarize_url(
    media_url="https://www.youtube.com/watch?v=...",
    style="concise",
    youtube=True,
)
print(res2["summary"])  # raw in res2["raw"]
```

Notes
- This implementation follows the current v1 SDK (indexes + tasks). Twelve Labs uses `index_id` (not projects) to group videos.
- To avoid downloading YouTube locally, the service tries in order:
  1) RapidAPI (if configured) to get a progressive MP4 URL (e.g., itag 22/18).
  2) yt_dlp metadata-only extraction (no download) for a direct URL.
  3) Local download via yt_dlp (only if the above fail and `TWELVE_LABS_ALLOW_YT_DOWNLOAD` is true).
  - If resolution fails or `yt_dlp` is not installed, provide a direct video URL instead.
  - Twelve Labs requires a direct, playable media URL. Generic YouTube watch pages aren’t accepted as-is.
- The service polls for video indexing and then runs summarization. Defaults are 10s poll interval and 30m timeout; tweak in `TwelveLabsConfig` if needed.
