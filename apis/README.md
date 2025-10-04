Swipe Service API (FastAPI)

Overview
- FastAPI wrapper around the Python Twelve Labs summarization service.
- Provides a simple HTTP endpoint to summarize a YouTube or direct video URL.

Install
- pip install -r apis/requirements.txt

Env
- Uses values from service/.env (API keys, index id, RapidAPI config).
  - You can export envs directly instead if you prefer.

Run (dev)
- uvicorn apis.main:app --reload

Endpoints
- POST /summarize
  - Body JSON:
    { "youtube_url": "https://www.youtube.com/watch?v=...", "style": "concise", "language": "en", "allow_download": true }
    or { "video_url": "https://example.com/video.mp4" }
  - Response JSON: { "video_id": str, "summary": str, "raw": object }

Notes
- If RapidAPI/metadata cannot produce a directly-fetchable URL, and allow_download is true (or env allows it), the service downloads via yt-dlp and uploads the file to Twelve Labs.
- To strictly avoid local downloads, set allow_download=false on the request or TWELVE_LABS_ALLOW_YT_DOWNLOAD=false in env.
