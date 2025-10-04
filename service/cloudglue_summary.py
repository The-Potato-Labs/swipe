"""
Cloudglue YouTube/direct video summarization service (Python).

This module integrates with the Cloudglue API to:
- Ensure a collection (by id or name)
- Ingest a YouTube URL or direct video URL
- Wait for processing to complete
- Request a multimodal description/summary

Env expected
- CLOUDGLUE_API_KEY (required)
- CLOUDGLUE_BASE_URL (optional; default: https://api.cloudglue.dev)
- CLOUDGLUE_COLLECTION_ID (optional; recommended to avoid lookups)
- CLOUDGLUE_COLLECTION_NAME (optional; default: swipe)

Notes
- Cloudglue docs: https://docs.cloudglue.dev/introduction
- Endpoints inferred from API reference sitemap; shapes may vary slightly by
  version. This wrapper attempts common payloads and gracefully falls back.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass
class CloudglueConfig:
    api_key: str
    base_url: str = "https://api.cloudglue.dev"
    collection_id: Optional[str] = None
    collection_name: str = "swipe"
    poll_interval_sec: float = 5.0
    timeout_sec: int = 60 * 20


class CloudglueError(RuntimeError):
    pass


class CloudglueSummarizer:
    def __init__(self, config: CloudglueConfig):
        self.config = config
        self._session = requests.Session()
        # Support both Bearer and x-api-key styles to match Cloudglue auth
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.config.api_key}",
                "x-api-key": self.config.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self._debug = os.getenv("CLOUDGLUE_DEBUG", "false").lower() == "true"

    @classmethod
    def from_env(cls) -> "CloudglueSummarizer":
        api_key = os.getenv("CLOUDGLUE_API_KEY")
        if not api_key:
            raise ValueError("Missing CLOUDGLUE_API_KEY")
        return cls(
            CloudglueConfig(
                api_key=api_key,
                base_url=os.getenv("CLOUDGLUE_BASE_URL", "https://api.cloudglue.dev"),
                collection_id=os.getenv("CLOUDGLUE_COLLECTION_ID") or None,
                collection_name=os.getenv("CLOUDGLUE_COLLECTION_NAME", "swipe"),
            )
        )

    # Public API -----------------------------------------------------------
    def summarize_url(
        self,
        media_url: str,
        *,
        style: Optional[str] = None,
        language: Optional[str] = None,
        youtube: bool = False,
    ) -> Dict[str, Any]:
        collection_id = self._ensure_collection()
        file_id = (
            self._ingest_youtube(collection_id, media_url)
            if youtube
            else self._ingest_direct_url(collection_id, media_url)
        )
        self._wait_file_ready(file_id)
        summary = self._describe(file_id=file_id, style=style, language=language)
        return {
            "collection_id": collection_id,
            "file_id": file_id,
            "summary": self._extract_summary_text(summary) or "",
            "raw": summary,
        }

    # Internals: Collections ----------------------------------------------
    def _ensure_collection(self) -> str:
        if self.config.collection_id:
            return self.config.collection_id

        # Try creating; if name conflicts, attempt to find by name via list
        # Try creation with alternative field names
        for body in (
            {"name": self.config.collection_name},
            {"collectionName": self.config.collection_name},
            {"label": self.config.collection_name},
        ):
            try:
                r = self._session.post(
                    f"{self.config.base_url}/collections",
                    json=body,
                    timeout=20,
                )
            except requests.RequestException as e:
                raise CloudglueError(f"collections POST failed: {e}")
            if r.status_code in (200, 201):
                try:
                    data = r.json()
                except Exception:
                    data = {}
                cid = (
                    (data.get("data") or {}).get("id")
                    if isinstance(data.get("data"), dict)
                    else data.get("id")
                    or data.get("_id")
                    or data.get("collectionId")
                )
                if not cid:
                    # Attempt to read Location header
                    loc = r.headers.get("Location")
                    if loc and "/collections/" in loc:
                        cid = loc.rsplit("/", 1)[-1]
                if cid:
                    self.config.collection_id = cid
                    return cid
                # If created but no id, break to fallback list
                break
            # If conflict or bad request, proceed to fallback lookup

        # Fallback: try to list and match by name if server returned 409 etc.
        # Fallback: list collections and match by name, trying different shapes
        list_params = (
            {"name": self.config.collection_name},
            {"collectionName": self.config.collection_name},
            {},
        )
        for params in list_params:
            try:
                r = self._session.get(
                    f"{self.config.base_url}/collections", params=params, timeout=20
                )
            except requests.RequestException:
                continue
            if not r.ok:
                continue
            try:
                data = r.json()
            except Exception:
                continue
            items = (
                data
                if isinstance(data, list)
                else data.get("data")
                if isinstance(data.get("data"), list)
                else data.get("collections")
                if isinstance(data.get("collections"), list)
                else []
            )
            for it in items:
                n = it.get("name") or it.get("collection_name") or it.get("label")
                if n == self.config.collection_name:
                    cid = it.get("id") or it.get("_id") or it.get("collectionId")
                    if cid:
                        self.config.collection_id = cid
                        return cid
        raise CloudglueError(
            "Unable to resolve or create collection id. Set CLOUDGLUE_COLLECTION_ID to skip lookups."
        )

    # Internals: Ingest ----------------------------------------------------
    def _ingest_youtube(self, collection_id: str, youtube_url: str) -> str:
        """
        Prefer downloading the YouTube video locally and uploading the file to
        Cloudglue (robust against IP-bound/expiring links). If download fails,
        fall back to Cloudglue's URL-based ingest endpoints.
        """
        # 1) Try local download + file upload first
        temp_path = _download_youtube_to_temp(youtube_url)
        if temp_path:
            try:
                fid = self._upload_file(collection_id, temp_path)
                if fid:
                    return fid
            finally:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

        # 2) Fallback: Cloudglue YouTube/URL ingest
        endpoints = [
            (
                f"{self.config.base_url}/collections/youtube",
                [
                    {"collectionId": collection_id, "url": youtube_url},
                    {"collectionId": collection_id, "youtubeUrl": youtube_url},
                ],
            ),
            (
                f"{self.config.base_url}/collections/{collection_id}/youtube",
                [
                    {"url": youtube_url},
                    {"youtubeUrl": youtube_url},
                ],
            ),
        ]
        for ep, bodies in endpoints:
            for body in bodies:
                try:
                    r = self._session.post(ep, json=body, timeout=45)
                except requests.RequestException as e:
                    if self._debug:
                        print(f"cloudglue POST {ep} error: {e}")
                    continue
                if r.ok:
                    try:
                        data = r.json()
                    except Exception:
                        data = {}
                    fid = data.get("fileId") or data.get("id") or data.get("_id")
                    if fid:
                        return fid
                else:
                    if self._debug:
                        txt = (r.text or "")[:200]
                        print(f"cloudglue POST {ep} {r.status_code}: {txt}")
        # 3) Final fallback: generic files upload by URL inside the collection
        return self._ingest_direct_url(collection_id, youtube_url)

    def _ingest_direct_url(self, collection_id: str, url: str) -> str:
        candidates = [
            (f"{self.config.base_url}/collections/files", [{"collectionId": collection_id, "url": url}, {"collectionId": collection_id, "fileUrl": url}]),
            (f"{self.config.base_url}/collections/{collection_id}/files", [{"url": url}, {"fileUrl": url}]),
            (f"{self.config.base_url}/files", [{"collectionId": collection_id, "url": url}, {"collectionId": collection_id, "fileUrl": url}]),
        ]
        for ep, bodies in candidates:
            for body in bodies:
                try:
                    r = self._session.post(ep, json=body, timeout=45)
                except requests.RequestException as e:
                    if self._debug:
                        print(f"cloudglue POST {ep} error: {e}")
                    continue
                if r.ok:
                    try:
                        data = r.json()
                    except Exception:
                        data = {}
                    fid = data.get("fileId") or data.get("id") or data.get("_id")
                    if fid:
                        return fid
                else:
                    if self._debug:
                        txt = (r.text or "")[:200]
                        print(f"cloudglue POST {ep} {r.status_code}: {txt}")
        raise CloudglueError("Failed to create file from URL")

    def _upload_file(self, collection_id: str, file_path: str) -> Optional[str]:
        """
        Upload a local file using multipart/form-data to Cloudglue. Tries common
        endpoints and form field names.
        """
        filename = os.path.basename(file_path)
        # Try to determine a reasonable content type; default to mp4
        content_type = "video/mp4"
        endpoints = [
            (f"{self.config.base_url}/collections/files", True),
            (f"{self.config.base_url}/collections/{collection_id}/files", False),
            (f"{self.config.base_url}/files", True),
        ]
        for ep, needs_collection in endpoints:
            data = {"collectionId": collection_id} if needs_collection else {}
            try:
                with open(file_path, "rb") as fh:
                    files = {"file": (filename, fh, content_type)}
                    r = self._session.post(ep, data=data, files=files, timeout=120)
            except Exception as e:
                if self._debug:
                    print(f"cloudglue upload {ep} error: {e}")
                continue
            if r.ok:
                try:
                    data = r.json()
                except Exception:
                    data = {}
                fid = data.get("fileId") or data.get("id") or data.get("_id")
                if fid:
                    return fid
            else:
                if self._debug:
                    txt = (r.text or "")[:200]
                    print(f"cloudglue upload {ep} {r.status_code}: {txt}")
        return None


def _download_youtube_to_temp(url: str) -> Optional[str]:
    """
    Download a YouTube video to a temporary file using yt_dlp and return its path.
    """
    import tempfile
    try:
        import yt_dlp  # type: ignore
    except Exception:
        return None

    ydl_opts = {
        "quiet": True,
        "noprogress": True,
        "format": "mp4/best",
        "noplaylist": True,
        "outtmpl": os.path.join(tempfile.gettempdir(), "cloudglue-%(id)s.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if isinstance(info, dict):
                return ydl.prepare_filename(info)
    except Exception:
        return None
    return None

    def _wait_file_ready(self, file_id: str) -> None:
        deadline = time.time() + self.config.timeout_sec
        last_status = None
        while True:
            try:
                r = self._session.get(f"{self.config.base_url}/files/{file_id}", timeout=15)
                if r.ok:
                    obj = r.json()
                    status = obj.get("status") or obj.get("state") or obj.get("processing_status")
                    last_status = status
                    if status in {"ready", "completed", "complete", "success", "done"}:
                        return
                    if status in {"failed", "error"}:
                        raise CloudglueError(f"File processing failed: {status}")
            except requests.RequestException:
                pass
            if time.time() > deadline:
                raise CloudglueError(f"Timed out waiting for file to be ready (last={last_status})")
            time.sleep(self.config.poll_interval_sec)

    # Internals: Describe/Summary -----------------------------------------
    def _describe(self, *, file_id: str, style: Optional[str], language: Optional[str]) -> Dict[str, Any]:
        prompt = _style_to_prompt(style, language)
        body = {"fileId": file_id}
        if prompt:
            body["prompt"] = prompt
        try:
            r = self._session.post(f"{self.config.base_url}/describe", json=body, timeout=60)
            if r.ok:
                try:
                    return r.json()
                except Exception as e:  # noqa: BLE001
                    raise CloudglueError(f"Describe JSON decode failed: {e}")
        except requests.RequestException as e:
            raise CloudglueError(f"Describe failed: {e}")
        raise CloudglueError(f"Describe HTTP {r.status_code}: {r.text[:200]}")

    @staticmethod
    def _extract_summary_text(payload: Dict[str, Any]) -> Optional[str]:
        # Try common locations
        candidates = [
            ("summary",),
            ("data", "summary"),
            ("result", "summary"),
            ("description",),
            ("text",),
        ]
        for path in candidates:
            node: Any = payload
            for key in path:
                if isinstance(node, dict) and key in node:
                    node = node[key]
                else:
                    node = None
                    break
            if isinstance(node, str):
                return node
        return None


def _style_to_prompt(style: Optional[str], language: Optional[str]) -> Optional[str]:
    if not style and not language:
        return None
    lang = language or ""
    if style:
        s = style.lower().strip()
        if s in {"concise", "brief", "short"}:
            return f"Write a concise summary in {lang} with 3-5 bullet points.".strip()
        if s in {"detailed", "long", "thorough"}:
            return f"Write a detailed summary in {lang} focusing on key points and takeaways.".strip()
        return style
    return f"Write a summary in {lang}.".strip()
