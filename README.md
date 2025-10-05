# Swipe Monorepo

Swipe pairs a Next.js client with Python services that summarize and analyze YouTube content using Twelve Labs and Cloudglue. Use this README to boot the app locally and understand how the pieces fit together.

## Repository Layout

- `client/` – Next.js 15 app that surfaces sponsorship search and calls the Python APIs.
- `service/` – Python helpers and CLI wrappers around the Twelve Labs and Cloudglue SDKs.
- `apis/` – FastAPI wrapper that exposes the Python services over HTTP.

## Prerequisites

- Node.js 18.18+ (ensure `npm -v` works).
- Python 3.9+ with `pip`.
- (Optional) `uvicorn`/`fastapi` tooling if you plan to run the API wrapper.

## Environment Variables

Create your own secrets; the checked-in `.env` files are examples.

### Frontend (`client/.env.local`)

- `NEXT_PUBLIC_UPRIVER_API_KEY` – API key for Upriver sponsorship lookups.

### Python Services (`service/.env`)

- `TWELVE_LABS_API_KEY` – Twelve Labs API key.
- `TWELVE_LABS_INDEX_ID` / `TWELVE_LABS_INDEX_NAME` – target index configuration.
- `TWELVE_LABS_ALLOW_YT_DOWNLOAD` – allow yt-dlp fallback when needed.
- `REDIS_URL` or Upstash credentials – optional caching layer.
- `YT_RAPIDAPI_*` – optional RapidAPI resolver for direct YouTube URLs.
- `YT_DLP_COOKIES_FROM_BROWSER` – optional browser name (`chrome`, `brave`, `edge`, `firefox`) so yt-dlp can load local cookies for restricted videos.

You can export these in your shell instead of relying on `.env` files.

## Setup

### 1. Install client dependencies

```bash
cd client
npm install
```

### 2. Install Python dependencies

```bash
cd service
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If you will run the FastAPI wrapper, also install its requirements:

```bash
cd apis
pip install -r requirements.txt
```

## Running the Apps

### Next.js client

```bash
cd client
npm run dev
# Visit http://localhost:3000
```

The client calls the Upriver sponsorship API via the `/api/sponsorships` route, which forwards your query with the configured API key.

### Python CLI helpers

From the `service/` directory after activating the virtual environment:

```bash
python -m service.cli --provider twelvelabs --youtube-url https://www.youtube.com/watch?v=VIDEO_ID
```

Switch `--provider cloudglue` to use the Cloudglue summarizer or call `python -m service.twelvelabs_analyze_brand` for brand-focused analysis.

### FastAPI service (optional)

```bash
cd apis
uvicorn apis.main:app --reload
```

Then POST to `http://127.0.0.1:8000/summarize` with a JSON body containing `youtube_url` (or `video_url`) and optional `style`, `language`, and `provider` fields.

## Development Notes

- yt-dlp tries RapidAPI resolution first (if configured) and falls back to local downloads; set `TWELVE_LABS_ALLOW_YT_DOWNLOAD=false` to disable downloads entirely.
- When using browser cookies (`YT_DLP_COOKIES_FROM_BROWSER`), ensure the chosen browser is installed and signed into a profile that can access the requested videos.
- Redis/Upstash caching is optional; if credentials are missing the services run without persistence.

## Testing & Linting

- Frontend lint: `npm run lint` inside `client`.
- Python formatting/tests are not bundled; add your preferred tooling (e.g., `ruff`, `pytest`) as needed.

## Deployment Outline

- Deploy the Next.js app to Vercel or another Node host with `NEXT_PUBLIC_UPRIVER_API_KEY` set.
- Deploy the Python FastAPI service (or CLI) where Twelve Labs credentials are available. Container images should install `service/requirements.txt` and, if using the HTTP API, `apis/requirements.txt`.
