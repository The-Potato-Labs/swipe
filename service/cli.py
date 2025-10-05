"""
Small CLI to summarize a YouTube (or direct) video URL using Twelve Labs or Cloudglue.

Usage examples:
    export TWELVE_LABS_API_KEY=...  # required
    # optionally:
    # export TWELVE_LABS_INDEX_ID=...
    # export TWELVE_LABS_INDEX_NAME=swipe-summaries
    # export TWELVE_LABS_ENABLE_MARENGO=false
    # export TWELVE_LABS_LANGUAGE=en
    # export TWELVE_LABS_ALLOW_YT_DOWNLOAD=true  # fallback to local download if needed
    # Cloudglue (if using provider=cloudglue):
    # export CLOUDGLUE_API_KEY=...
    # export CLOUDGLUE_COLLECTION_ID=...  (recommended)

    python -m service.cli --provider twelvelabs --youtube-url https://www.youtube.com/watch?v=...
    python -m service.cli --provider cloudglue  --youtube-url https://www.youtube.com/watch?v=...

Returns JSON with keys: video_id (for TL), collection_id/file_id (for Cloudglue), summary, raw
"""

from __future__ import annotations

import argparse
import json
import sys

import os
from .twelvelabs_summary import TwelveLabsSummarizer
from .cloudglue_summary import CloudglueSummarizer
from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Summarize a YouTube (or direct) video URL via Twelve Labs or Cloudglue"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--youtube-url", help="YouTube video URL to summarize")
    group.add_argument("--video-url", help="Direct video URL (mp4, etc.)")
    parser.add_argument(
        "--style",
        default=None,
        help="Optional style hint for the summary (e.g., concise)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Language code for the summary (default: env or 'en')",
    )
    parser.add_argument(
        "--provider",
        choices=["twelvelabs", "cloudglue"],
        default=os.getenv("SUMMARY_PROVIDER", "twelvelabs"),
        help="Provider to use (default: twelvelabs)",
    )
    args = parser.parse_args(argv)

    url = args.youtube_url or args.video_url
    if args.provider == "cloudglue":
        summarizer = CloudglueSummarizer.from_env()
        result = summarizer.summarize_url(
            media_url=url,
            style=args.style,
            language=args.language,
            youtube=bool(args.youtube_url),
        )
    else:
        summarizer = TwelveLabsSummarizer.from_env()
        result = summarizer.summarize_youtube(
            youtube_url=url,
            style=args.style,
            language=args.language,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
