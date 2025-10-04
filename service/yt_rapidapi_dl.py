"""
YouTube → Direct Media URL via RapidAPI (yt-api.p.rapidapi.com)

This helper calls the documented RapidAPI endpoint to retrieve streaming data
for a YouTube video and extracts a progressive MP4 URL suitable for ingestion
by Twelve Labs (or any other service that needs a direct, playable media URL).

Env vars
- RAPIDAPI_API_KEY (required)
- YT_API_CGEO (optional; e.g., "US", "DE" — controls region)

Endpoint
- GET https://yt-api.p.rapidapi.com/dl?id=<videoId>&cgeo=<region>
  headers:
    x-rapidapi-host: yt-api.p.rapidapi.com
    x-rapidapi-key: $RAPIDAPI_API_KEY

Usage
    from service.yt_rapidapi_dl import resolve_youtube_direct_url
    url = resolve_youtube_direct_url("https://www.youtube.com/watch?v=...", cgeo="DE")
    if url is None:
        print("No direct URL found")

Notes
- Prefers progressive MP4 with audio (itag 22→18) when available.
- Returns None if a usable URL cannot be found or the request fails.
"""

from __future__ import annotations

import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import requests


RAPIDAPI_HOST_DEFAULT = "yt-api.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST_DEFAULT}/dl"


def resolve_youtube_direct_url(
    youtube_url: str,
    *,
    api_key: Optional[str] = None,
    cgeo: Optional[str] = None,
    timeout: float = 20.0,
) -> Optional[str]:
    """
    Resolve a progressive MP4 URL for the given YouTube video using RapidAPI.

    Returns a direct media URL string or None if not available.
    """
    api_key = api_key or os.getenv("RAPIDAPI_API_KEY")
    if not api_key:
        return None

    vid = _extract_youtube_id(youtube_url)
    params = {"id": vid} if vid else {"url": youtube_url}
    cgeo = cgeo or os.getenv("YT_API_CGEO")
    if cgeo:
        params["cgeo"] = cgeo

    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST_DEFAULT,
        "x-rapidapi-key": api_key,
    }
    try:
        resp = requests.get(
            RAPIDAPI_BASE_URL, headers=headers, params=params, timeout=timeout
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    return _pick_progressive_mp4(data)


def _pick_progressive_mp4(data: Dict[str, Any]) -> Optional[str]:
    def pick_from_list(items):
        if not isinstance(items, list):
            return None
        best22 = None
        best18 = None
        best_mp4 = None
        for it in items:
            if not isinstance(it, dict):
                continue
            url = it.get("url")
            mime = it.get("mime") or it.get("type")
            itag = str(it.get("itag")) if it.get("itag") is not None else None
            if not url:
                continue
            if itag == "22":
                best22 = url
            elif itag == "18":
                best18 = url
            if (mime and "video/mp4" in mime) and best_mp4 is None:
                best_mp4 = url
        return best22 or best18 or best_mp4

    # Typical shapes: top-level `formats`, or nested under `streamingData`.
    for path in (
        ("formats",),
        ("streamingData", "formats"),
    ):
        node: Any = data  # type: ignore[assignment]
        ok = True
        for k in path:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok:
            url = pick_from_list(node)
            if url:
                return url
    # Some endpoints also include `adaptiveFormats` (video-only); avoid if possible.
    return None


def _extract_youtube_id(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        if parsed.netloc.endswith("youtu.be"):
            vid = parsed.path.lstrip("/")
            return vid or None
        if parsed.netloc.endswith("youtube.com"):
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [None])[0]
            return vid
    except Exception:
        return None
    return None
