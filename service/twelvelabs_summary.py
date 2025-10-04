"""
Twelve Labs YouTube summarization service (Python).

This module provides a minimal, production-friendly wrapper to take a YouTube
URL (or any direct video URL), ingest it into Twelve Labs, wait for processing,
and request a summary.

Notes and assumptions:
- Uses the official Twelve Labs Python SDK (`twelvelabs` v1.x).
- No external network calls are made here until you run it in your environment.
- You must provide `TWELVE_LABS_API_KEY` via environment variable.
- Provide an index via `TWELVE_LABS_INDEX_ID`. If omitted, the service will
  resolve or create an index by name.

If you don't yet have the SDK installed:
    pip install twelvelabs

The exact API surface may vary by SDK version; this wrapper is structured so
you can easily adjust the client calls to match your installed SDK.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs


class _SDKNotInstalled(RuntimeError):
    pass


def _require_sdk():
    try:
        # The official Twelve Labs SDK is typically available as `twelvelabs`.
        # Import lazily to keep module import cheap and friendly to environments
        # where the SDK isn't yet installed.
        from twelvelabs import TwelveLabs  # type: ignore

        return TwelveLabs
    except Exception as exc:  # noqa: BLE001
        raise _SDKNotInstalled(
            "The 'twelvelabs' Python SDK is required. Install with:\n"
            "    pip install twelvelabs\n"
            "Then retry."
        ) from exc


@dataclass
class TwelveLabsConfig:
    api_key: str
    project_id: Optional[str] = None
    project_name: str = "swipe-summaries"
    # Index config
    index_id: Optional[str] = None
    index_name: str = "swipe-summaries"
    # Models: defaults optimized for summarization (Pegasus only)
    enable_pegasus: bool = True
    enable_marengo: bool = False  # set True if you also want search/embeddings
    model_options: tuple[str, ...] = ("visual", "audio")
    # Summarization config
    language: str = "en"
    poll_interval_sec: float = 10.0
    timeout_sec: int = 60 * 30  # 30 minutes default
    # Fallbacks
    allow_youtube_download_fallback: bool = True
    # Optional RapidAPI resolver for YouTube → direct media URL
    yt_rapidapi_url: Optional[str] = None
    yt_rapidapi_host: Optional[str] = None
    yt_rapidapi_key: Optional[str] = None


class TwelveLabsSummarizer:
    """
    High-level YouTube → Twelve Labs → Summary workflow.

    Usage:
        summarizer = TwelveLabsSummarizer.from_env()
        result = summarizer.summarize_youtube(
            youtube_url="https://www.youtube.com/watch?v=...",
            style="concise",
        )
        print(result["summary"])  # or inspect the full payload
    """

    def __init__(self, config: TwelveLabsConfig):
        self.config = config
        TwelveLabs = _require_sdk()  # noqa: N806
        # Optional: pass headers if you need to target a specific organization.
        # Most users don't need this.
        headers = None
        org_id = os.getenv("TWELVE_LABS_ORGANIZATION_ID")
        if org_id:
            # Header name varies in some docs; the SDK accepts arbitrary headers.
            # If this header does not work in your account, consult the org docs
            # and update the key accordingly.
            headers = {"X-Organization-Id": org_id}

        self._client = TwelveLabs(api_key=self.config.api_key, headers=headers)

    @classmethod
    def from_env(cls) -> "TwelveLabsSummarizer":
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if not api_key:
            raise ValueError("Missing TWELVE_LABS_API_KEY. Set it in your environment.")
        # Defaults for the RapidAPI-based YouTube resolver
        default_rapidapi_url = (
            os.getenv("YT_RAPIDAPI_URL") or "https://yt-api.p.rapidapi.com/dl"
        )
        default_rapidapi_host = os.getenv("YT_RAPIDAPI_HOST") or "yt-api.p.rapidapi.com"
        rapidapi_key = os.getenv("YT_RAPIDAPI_KEY") or os.getenv("RAPIDAPI_API_KEY")

        cfg = TwelveLabsConfig(
            api_key=api_key,
            index_id=os.getenv("TWELVE_LABS_INDEX_ID") or None,
            index_name=os.getenv("TWELVE_LABS_INDEX_NAME", "swipe-summaries"),
            enable_pegasus=(
                os.getenv("TWELVE_LABS_ENABLE_PEGASUS", "true").lower() != "false"
            ),
            enable_marengo=(
                os.getenv("TWELVE_LABS_ENABLE_MARENGO", "false").lower() == "true"
            ),
            language=os.getenv("TWELVE_LABS_LANGUAGE", "en"),
            allow_youtube_download_fallback=(
                os.getenv("TWELVE_LABS_ALLOW_YT_DOWNLOAD", "true").lower() != "false"
            ),
            yt_rapidapi_url=default_rapidapi_url,
            yt_rapidapi_host=default_rapidapi_host,
            yt_rapidapi_key=rapidapi_key,
        )
        return cls(cfg)

    # --- Public API -----------------------------------------------------
    def summarize_youtube(
        self,
        youtube_url: str,
        *,
        style: Optional[str] = None,
        language: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrate end-to-end summarization for a YouTube URL.

        Returns a dict containing at least: {"summary": str, ...}
        The exact payload mirrors the SDK's response.
        """
        index_id = self._ensure_index()

        video_id = self._ingest_from_url(index_id, youtube_url, metadata=metadata)
        self._wait_for_indexing_ready(index_id, video_id)

        summary_payload = self._summarize_video(
            video_id=video_id,
            style=style,
            language=language or self.config.language,
        )

        # Normalize a minimal contract for callers, while returning the full
        # payload in case upstream callers want to access more details.
        out = {
            "video_id": video_id,
            "summary": self._extract_summary_text(summary_payload) or "",
            "raw": summary_payload,
        }
        return out

    # --- Internals: Index ------------------------------------------------
    def _ensure_index(self) -> str:
        """
        Resolve an index_id (create if necessary) using the v1 SDK.
        """
        # Use provided index id when available
        if self.config.index_id:
            return self.config.index_id

        # Try resolve by name (IndexSchema uses `index_name`)
        for idx in self._client.indexes.list(index_name=self.config.index_name):
            if getattr(idx, "index_name", None) == self.config.index_name:
                self.config.index_id = getattr(idx, "id", None)
                if not self.config.index_id:
                    raise RuntimeError("Unable to resolve index id from SDK response.")
                return self.config.index_id

        # Create index
        from twelvelabs.indexes import IndexesCreateRequestModelsItem  # type: ignore

        models: list = []
        if self.config.enable_pegasus:
            models.append(
                IndexesCreateRequestModelsItem(
                    model_name="pegasus1.2",
                    model_options=list(self.config.model_options),
                )
            )
        if self.config.enable_marengo:
            models.append(
                IndexesCreateRequestModelsItem(
                    model_name="marengo2.7",
                    model_options=list(self.config.model_options),
                )
            )

        try:
            created = self._client.indexes.create(
                index_name=self.config.index_name, models=models
            )
            self.config.index_id = getattr(created, "id", None)
            if not self.config.index_id:
                raise RuntimeError(
                    "Index creation succeeded but id was not found in response."
                )
            return self.config.index_id
        except Exception:
            # If creation failed (e.g., 409 already exists), attempt to fetch existing by name
            for idx in self._client.indexes.list(index_name=self.config.index_name):
                if getattr(idx, "index_name", None) == self.config.index_name:
                    self.config.index_id = getattr(idx, "id", None)
                    if self.config.index_id:
                        return self.config.index_id
            raise

    # --- Internals: Ingest ----------------------------------------------
    def _ingest_from_url(
        self, index_id: str, url: str, *, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a video indexing task with a direct video URL.
        If a YouTube URL is provided, tries to resolve a temporary direct stream
        URL without downloading the file (requires `yt_dlp`).
        Returns the video_id.
        """
        video_url = url
        if _is_youtube_url(url):
            resolved = None
            # 1) Try RapidAPI resolver if configured
            if (
                self.config.yt_rapidapi_url
                and self.config.yt_rapidapi_key
                and self.config.yt_rapidapi_host
            ):
                resolved = _resolve_youtube_via_rapidapi(
                    url,
                    api_url=self.config.yt_rapidapi_url,
                    api_host=self.config.yt_rapidapi_host,
                    api_key=self.config.yt_rapidapi_key,
                )
            # 2) Try local metadata (no download) via yt_dlp
            if not resolved:
                resolved = _resolve_youtube_direct_url(url)

            if resolved:
                video_url = resolved
            elif not self.config.allow_youtube_download_fallback:
                raise RuntimeError(
                    "Unable to resolve a direct stream URL from YouTube and fallback disabled."
                )

        try:
            task = self._client.tasks.create(index_id=index_id, video_url=video_url)
        except Exception as e:
            if _is_youtube_url(url) and self.config.allow_youtube_download_fallback:
                temp_path = _download_youtube_to_temp(url)
                if not temp_path:
                    raise RuntimeError(
                        "Direct YouTube URL not accepted and yt_dlp fallback failed. "
                        "Install yt-dlp or provide a direct video URL."
                    ) from e
                try:
                    with open(temp_path, "rb") as fh:
                        task = self._client.tasks.create(
                            index_id=index_id, video_file=fh
                        )
                finally:
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
            else:
                raise
        task_id = getattr(task, "id", None) or getattr(task, "_id", None)
        if not task_id:
            raise RuntimeError("Task creation response missing id.")
        # Wait for indexing to complete and retrieve final video_id
        done = self._wait_for_task(task_id)
        if getattr(done, "status", None) != "ready":
            raise RuntimeError(
                f"Indexing failed: status={getattr(done, 'status', None)}"
            )
        video_id = getattr(done, "video_id", None)
        if not video_id:
            raise RuntimeError("Indexing completed but video_id missing in response.")
        return video_id

    def _wait_for_task(self, task_id: str):
        deadline = time.time() + self.config.timeout_sec
        while True:
            resp = self._client.tasks.retrieve(task_id)
            status = getattr(resp, "status", None)
            if status in {"ready", "failed"}:
                return resp
            if time.time() > deadline:
                raise TimeoutError("Timed out waiting for indexing task.")
            time.sleep(self.config.poll_interval_sec)

    def _wait_for_indexing_ready(self, index_id: str, video_id: str) -> None:
        """
        Safety check: retrieve video info until it's accessible in the index.
        """
        deadline = time.time() + self.config.timeout_sec
        while True:
            try:
                _ = self._client.indexes.videos.retrieve(
                    index_id=index_id, video_id=video_id
                )
                return
            except Exception:
                if time.time() > deadline:
                    raise TimeoutError("Timed out waiting for video to be retrievable.")
                time.sleep(self.config.poll_interval_sec)

    # --- Internals: Summary --------------------------------------------
    def _summarize_video(
        self, *, video_id: str, style: Optional[str], language: str
    ) -> Dict[str, Any]:
        prompt = _style_to_prompt(style, language)
        res = self._client.summarize(video_id=video_id, type="summary", prompt=prompt)
        # Convert to dict for a stable output contract
        if hasattr(res, "model_dump"):
            try:
                return res.model_dump()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        if isinstance(res, dict):
            return res
        return res.__dict__  # type: ignore[attr-defined]

    # --- Internals: Helpers --------------------------------------------
    @staticmethod
    def _extract_summary_text(summary_payload: Dict[str, Any]) -> str:
        # Try common locations for the summary text depending on SDK/object.
        candidates = [
            ("result", "summary"),
            ("data", "summary"),
            ("summary",),
            ("output",),
        ]
        for path in candidates:
            node: Any = summary_payload
            ok = True
            for key in path:
                if isinstance(node, dict) and key in node:
                    node = node[key]
                else:
                    ok = False
                    break
            if ok and isinstance(node, str):
                return node
        # Fallback to empty string if the structure is unexpected
        return ""


def _is_youtube_url(url: str) -> bool:
    return any(host in url for host in ("youtube.com", "youtu.be"))


def _resolve_youtube_direct_url(url: str) -> Optional[str]:
    """
    Resolve a temporary direct media URL for a YouTube video without downloading it.
    Requires `yt_dlp` installed. Returns None if resolution fails.
    """
    try:
        import yt_dlp  # type: ignore
    except Exception:
        return None

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "format": "best[ext=mp4]/best",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Prefer direct URL if available
            direct_url = info.get("url") if isinstance(info, dict) else None
            if direct_url:
                return direct_url
            # Try formats list
            formats = info.get("formats") if isinstance(info, dict) else None
            if isinstance(formats, list):
                for fmt in reversed(formats):
                    u = fmt.get("url")
                    if u:
                        return u
    except Exception:
        return None
    return None


def _resolve_youtube_via_rapidapi(
    youtube_url: str, *, api_url: str, api_host: str, api_key: str
) -> Optional[str]:
    """
    Use a RapidAPI endpoint that returns YouTube streaming data (with
    `formats`/`adaptiveFormats`) to extract a direct progressive MP4 URL.

    Expects a response structure similar to service/yt-api.json.
    """
    try:
        import requests  # type: ignore
    except Exception:
        return None

    vid = _extract_youtube_id(youtube_url)
    params = {"id": vid} if vid else {"url": youtube_url}
    cgeo = os.getenv("YT_API_CGEO")
    if cgeo:
        params["cgeo"] = cgeo
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": api_host,
    }
    try:
        resp = requests.get(api_url, headers=headers, params=params, timeout=20)
        if resp.status_code != 200:
            return None
        data = resp.json()
    except Exception:
        return None

    # Prefer progressive MP4 with audio: itag 22 (720p) then 18 (360p)
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

    # Typical shapes: top-level `formats`, `adaptiveFormats` or nested under e.g. `streamingData`.
    url = None
    for path in (
        ("formats",),
        ("streamingData", "formats"),
        ("streamingData", "adaptiveFormats"),
        ("adaptiveFormats",),
    ):
        node = data
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
            break
    return url


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


def _download_youtube_to_temp(url: str) -> Optional[str]:
    """
    Download a YouTube video to a temporary file using yt_dlp and return its path.
    The caller is responsible for deleting the file.
    """
    import tempfile

    try:
        import yt_dlp  # type: ignore
    except Exception:
        return None

    ydl_opts = {
        "quiet": True,
        "format": "mp4/best",
        "noplaylist": True,
        "outtmpl": os.path.join(tempfile.gettempdir(), "twelvelabs-%(id)s.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if isinstance(info, dict):
                return ydl.prepare_filename(info)
    except Exception:
        return None
    return None


def _style_to_prompt(style: Optional[str], language: str) -> Optional[str]:
    if not style:
        return None
    s = style.lower().strip()
    if s in {"concise", "brief", "short"}:
        return f"Write a concise summary in {language} with 3-5 bullet points."
    if s in {"detailed", "long", "thorough"}:
        return f"Write a detailed summary in {language} focusing on key points and takeaways."
    # Default: treat as a free-text instruction
    return style
