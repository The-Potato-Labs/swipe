"""
Small CLI to summarize a YouTube (or direct) video URL using Twelve Labs.

Usage examples:
    export TWELVE_LABS_API_KEY=...  # required
    # optionally:
    # export TWELVE_LABS_INDEX_ID=...
    # export TWELVE_LABS_INDEX_NAME=swipe-summaries
    # export TWELVE_LABS_ENABLE_MARENGO=false
    # export TWELVE_LABS_LANGUAGE=en
    # export TWELVE_LABS_ALLOW_YT_DOWNLOAD=true  # fallback to local download if needed

    python -m service.cli --youtube-url https://www.youtube.com/watch?v=...

Returns JSON with keys: video_id, summary, raw
"""

from __future__ import annotations

import argparse
import json
import sys

from .twelvelabs_summary import TwelveLabsSummarizer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize a YouTube (or direct) video URL via Twelve Labs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--youtube-url", help="YouTube video URL to summarize")
    group.add_argument("--video-url", help="Direct video URL (mp4, etc.)")
    parser.add_argument("--style", default=None, help="Optional style hint for the summary (e.g., concise)")
    parser.add_argument("--language", default=None, help="Language code for the summary (default: env or 'en')")
    args = parser.parse_args(argv)

    summarizer = TwelveLabsSummarizer.from_env()
    url = args.youtube_url or args.video_url
    result = summarizer.summarize_youtube(
        youtube_url=url,
        style=args.style,
        language=args.language,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
