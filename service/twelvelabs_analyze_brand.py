"""
Twelve Labs Analyze integration for brand-focused video analysis.

This module provides a small wrapper around the Twelve Labs `analyze` endpoint
that:
- Builds a structured prompt (with a {brand} placeholder) to analyze a specific
  video already indexed in Twelve Labs.
- Constrains the response to a strict JSON Schema using the SDK's
  `ResponseFormat(type='json_schema', json_schema=...)` so that the output is
  machine-parseable.

Usage (programmatic):
    from service.twelvelabs_analyze_brand import TwelveLabsBrandAnalyzer

    analyzer = TwelveLabsBrandAnalyzer.from_env()
    # Either analyze an already-indexed video_id
    result1 = analyzer.analyze_video(video_id="<VIDEO_ID>", brand="Nike")
    # Or provide a YouTube/direct URL and the service will ingest then analyze
    result2 = analyzer.analyze(
        brand="Nike",
        youtube_url="https://www.youtube.com/watch?v=...",  # or video_url="https://...mp4"
    )
    print(result2["json"])  # parsed JSON (dict)

To run as a script:
    # With a video_id
    python -m service.twelvelabs_analyze_brand --brand "Nike" --video-id <VIDEO_ID>
    # Or with a URL (YouTube or direct)
    python -m service.twelvelabs_analyze_brand --brand "Nike" --youtube-url https://www.youtube.com/watch?v=...
    python -m service.twelvelabs_analyze_brand --brand "Nike" --video-url https://example.com/video.mp4

Requirements:
- twelvelabs==1.x (already in service/requirements.txt)
- Optional: python-dotenv for .env loading (same as other service modules)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class _SDKNotInstalled(RuntimeError):
    pass


def _require_sdk():
    try:
        from twelvelabs import TwelveLabs  # type: ignore
        from twelvelabs.types.response_format import ResponseFormat  # type: ignore

        return TwelveLabs, ResponseFormat
    except Exception as exc:  # noqa: BLE001
        raise _SDKNotInstalled(
            "The 'twelvelabs' Python SDK is required. Install with:\n"
            "    pip install twelvelabs\n"
            "Then retry."
        ) from exc


from datetime import datetime, timezone
from time import perf_counter
from .brand_analysis_models import (
    BrandAnalysisOutput,
    BrandAnalysisMeta,
    BrandAnalysisResult,
    ErrorDetail,
)


# Prompt template; runtime injects the brand and the JSON Schema generated from
# Pydantic models via `BrandAnalysisOutput.model_json_schema()`.
PROMPT_TEMPLATE = (
    "You are a video analysis model. Analyze the given video and the target brand, "
    "and return a structured JSON object only — no text outside the JSON.\n\n"
    "Goal:\n"
    "Provide an overall summary, chapter titles and summaries, a comprehensive list of all brand mentions for the target brand, and include the main topics and hashtags.\n\n"
    "Brand to detect: {brand}\n\n"
    "Rules:\n"
    "- Output must be valid JSON matching the schema below.\n"
    "- Timestamps use HH:MM:SS (zero-padded). Chapters have non-overlapping start/end.\n"
    "- A brand mention is explicit when spoken, shown, or on-screen; implicit when inferred.\n"
    "- Topics should reflect the main themes (prefer lowercase snake_case).\n"
    "- Hashtags should be concise and relevant (3–8, standard #tag format).\n"
    "- Include start and end timestamps for every brand mention.\n"
    "- Keep sentences concise (under ~280 chars).\n"
    "- Never include any text outside the JSON.\n\n"
    "JSON schema:\n{json_schema}\n\n"
    "Instructions:\n"
    "1. Segment the video into meaningful chapters; fill id, title, summary, timestamps. The sponsor mentions should be their individual segments, if it's longer than 5 seconds.\n"
    "2. List all brand mentions across the entire video in brand_mentions. Use start and end timestamps if it's longer than 5 seconds, otherwise provide the start timestamp.\n"
    '3. Brand mentions can be of these types: brand_logo_placement, brand_name_text, brand_website_placement, brand_qr_code_placement, brand_coupon_placement, verbal_mention, product_visual, product_demo, comparison_section, call_to_action ("use code..."), affiliate_disclosure ("this video is sponsored by..."), giveaway_or_promo, and end_screen references.\n'
    "4. Brand mentions can overlay (e.g. there's a brand_logo_placement within the broader product_demo video segment).\n"
    "5. If none detected, return an empty array for brand_mentions.\n"
    "6. If a mention is not tied to a single chapter, omit chapter_id.\n"
    "7. Add main topics and 3–8 concise hashtags that reflect the video’s themes.\n"
    "8. Output strictly valid JSON (no markdown, no commentary).\n"
)


# Strict JSON Schema for the response_format to encourage structured output
BRAND_ANALYSIS_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "hashtags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "topics": {
            "type": "array",
            "items": {"type": "string"},
        },
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "timestamps": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                        },
                        "required": ["start", "end"],
                    },
                },
                "required": ["id", "title", "summary", "timestamps"],
            },
        },
        "brand_mentions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "mention_type": {"type": "string"},
                    "subtype": {"type": "string"},
                    "description": {"type": "string"},
                    "chapter_id": {"type": "string"},
                    "timestamps": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                        },
                        "required": ["start", "end"],
                    },
                    "placement": {"type": "string"},
                    "text": {"type": "string"},
                    "spoken_quote": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": [
                    "id",
                    "mention_type",
                    "description",
                    "timestamps",
                    "confidence",
                ],
            },
        },
    },
    "required": ["summary", "chapters", "brand_mentions", "hashtags", "topics"],
}


@dataclass
class TwelveLabsAnalyzeConfig:
    api_key: str
    # Index config
    index_id: Optional[str] = None
    index_name: str = "swipe-summaries"
    enable_pegasus: bool = True
    enable_marengo: bool = False
    model_options: tuple[str, ...] = ("visual", "audio")
    # Ingest config
    allow_youtube_download_fallback: bool = True
    # Timing
    poll_interval_sec: float = 10.0
    timeout_sec: int = 60 * 30
    # optional defaults for generation
    temperature: float = 0.2
    max_tokens: Optional[int] = None  # let the API default unless specified
    # Redis cache
    redis_url: Optional[str] = None
    redis_prefix: str = "ba:yt:"


class TwelveLabsBrandAnalyzer:
    def __init__(self, config: TwelveLabsAnalyzeConfig):
        self.config = config
        TwelveLabs, ResponseFormat = _require_sdk()
        # Optional org header
        headers = None
        org_id = os.getenv("TWELVE_LABS_ORGANIZATION_ID")
        if org_id:
            headers = {"X-Organization-Id": org_id}
        self._client = TwelveLabs(api_key=self.config.api_key, headers=headers)
        # Optional Redis client
        self._redis = _init_redis(self.config.redis_url)

    @classmethod
    def from_env(cls) -> "TwelveLabsBrandAnalyzer":
        # Keep consistent with existing modules that use dotenv
        from dotenv import load_dotenv

        # Load default .env (cwd) and also service/.env if present to be robust
        load_dotenv()
        try:
            here_env = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(here_env):
                load_dotenv(here_env, override=False)
        except Exception:
            pass
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if not api_key:
            raise ValueError("Missing TWELVE_LABS_API_KEY. Set it in your environment.")
        cfg = TwelveLabsAnalyzeConfig(
            api_key=api_key,
            index_id=os.getenv("TWELVE_LABS_INDEX_ID") or None,
            index_name=os.getenv("TWELVE_LABS_INDEX_NAME", "swipe-summaries"),
            enable_pegasus=(
                os.getenv("TWELVE_LABS_ENABLE_PEGASUS", "true").lower() != "false"
            ),
            enable_marengo=(
                os.getenv("TWELVE_LABS_ENABLE_MARENGO", "false").lower() == "true"
            ),
            allow_youtube_download_fallback=(
                os.getenv("TWELVE_LABS_ALLOW_YT_DOWNLOAD", "true").lower() != "false"
            ),
            redis_url=os.getenv("REDIS_URL") or None,
        )
        return cls(cfg)

    def _build_prompt(self, brand: str) -> str:
        # Generate JSON Schema from Pydantic models for inclusion in prompt
        schema = BrandAnalysisOutput.model_json_schema()
        schema_str = json.dumps(schema, ensure_ascii=False)
        return PROMPT_TEMPLATE.replace("{brand}", brand).replace(
            "{json_schema}", schema_str
        )

    def analyze_video(
        self,
        *,
        video_id: str,
        brand: str,
        source_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BrandAnalysisResult:
        """
        Run Twelve Labs analyze on a single video with the brand-focused prompt.

        Returns a dict with:
        - video_id: the input video id
        - json: parsed JSON object (or None if parsing failed)
        - raw: the SDK response as dict (contains raw 'data' string)
        - prompt: the effective prompt (for auditability)
        """
        prompt = self._build_prompt(brand)

        started = perf_counter()
        rf = (
            self._client.response_format
            if hasattr(self._client, "response_format")
            else None
        )
        # Construct ResponseFormat directly if client helper is absent
        if rf is None:
            try:
                # Prefer using the imported ResponseFormat type lazily
                from twelvelabs.types.response_format import ResponseFormat as _RF  # type: ignore

                rf = _RF(type="json_schema", json_schema=BRAND_ANALYSIS_SCHEMA)
            except Exception:
                rf = None
        resp = self._client.analyze(
            video_id=video_id,
            prompt=prompt,
            temperature=(
                temperature if temperature is not None else self.config.temperature
            ),
            response_format=rf,
            max_tokens=(
                max_tokens if max_tokens is not None else self.config.max_tokens
            ),
        )
        elapsed_ms = int((perf_counter() - started) * 1000)

        # Convert response into a stable dict form and parse JSON payload
        if hasattr(resp, "model_dump"):
            raw = resp.model_dump()
        else:  # pragma: no cover - fallback for unexpected SDK objects
            raw = {
                k: getattr(resp, k, None)
                for k in ("id", "data", "finish_reason", "usage")
            }

        errors: list[ErrorDetail] = []
        parsed_obj: Optional[BrandAnalysisOutput] = None
        data_text = raw.get("data")
        if isinstance(data_text, str):
            try:
                parsed_json = json.loads(data_text)
                try:
                    parsed_obj = BrandAnalysisOutput.model_validate(parsed_json)
                except Exception as ve:  # validation error
                    errors.append(
                        ErrorDetail(
                            code="validation_error",
                            message="Response did not match BrandAnalysisOutput schema.",
                            details={"error": str(ve)},
                        )
                    )
            except Exception as pe:
                errors.append(
                    ErrorDetail(
                        code="parse_error",
                        message="Response data was not valid JSON.",
                        details={"error": str(pe)},
                    )
                )
        else:
            errors.append(
                ErrorDetail(
                    code="missing_data",
                    message="Analyze response missing text 'data' field.",
                    details=None,
                )
            )

        if parsed_obj is None:
            # Provide a minimal empty payload to keep envelope stable
            parsed_obj = BrandAnalysisOutput(
                summary="",
                hashtags=[],
                topics=[],
                chapters=[],
                brand_mentions=[],
            )

        meta = BrandAnalysisMeta(
            provider="twelvelabs",
            brand=brand,
            video_id=video_id,
            index_id=self.config.index_id,
            source_url=source_url,
            created_at=datetime.now(timezone.utc),
            elapsed_ms=elapsed_ms,
            schema_version="brand_analysis.v1",
            schema_url="/openapi.json",
            trace_id=str(raw.get("id")) if raw.get("id") else None,
        )

        return BrandAnalysisResult(data=parsed_obj, meta=meta, errors=errors)

    # ---- Orchestration: ensure index, ingest or reuse, then analyze -------
    def analyze(
        self,
        *,
        brand: str,
        video_id: Optional[str] = None,
        youtube_url: Optional[str] = None,
        video_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BrandAnalysisResult:
        """
        High-level entrypoint: If a video_id is provided, analyze it directly.
        Otherwise, ingest the provided URL (YouTube or direct), wait for ready,
        then analyze using the brand-focused prompt.
        """
        # Support caching even if a YouTube link is provided via `video_url`.
        yt_id: Optional[str] = None
        if youtube_url:
            yt_id = _extract_youtube_id(youtube_url)
        elif video_url and _is_youtube_url(video_url):
            yt_id = _extract_youtube_id(video_url)
        # 1) If YouTube and cached analysis exists for (yt_id, brand), return it
        if yt_id and self._redis:
            key = _redis_key_analysis(self.config.redis_prefix, yt_id, brand)
            cached = _redis_get_json(self._redis, key)
            if cached:
                try:
                    print(f"[cache] hit analysis for yt:{yt_id} brand:{brand}")
                    return BrandAnalysisResult.model_validate(cached)
                except Exception:
                    pass  # corrupt cache; continue

        # 2) Resolve or ingest video_id
        if not video_id:
            url = youtube_url or video_url
            if not url:
                raise ValueError("Provide either video_id or youtube_url/video_url")
            index_id = self._ensure_index()

            # Reuse mapping ytid -> twelvelabs video_id if present
            if yt_id and self._redis:
                map_key = _redis_key_video_map(self.config.redis_prefix, yt_id)
                mapped = _redis_get_text(self._redis, map_key)
                if mapped:
                    print(f"[cache] hit mapping yt:{yt_id} -> video_id:{mapped}")
                    video_id = mapped

            if not video_id:
                print(f"[ingest] starting ingest for url: {url}")
                video_id = self._ingest_from_url(index_id, url, metadata=metadata)
                self._wait_for_indexing_ready(index_id, video_id)
                print(f"[ingest] indexing ready for video_id: {video_id}")
                # Store mapping
                if yt_id and self._redis:
                    map_key = _redis_key_video_map(self.config.redis_prefix, yt_id)
                    ok = _redis_set_text(self._redis, map_key, video_id)
                    print(
                        f"[cache] {'stored' if ok else 'FAILED to store'} mapping yt:{yt_id} -> video_id:{video_id}"
                    )

        # 3) Analyze
        print(f"[analyze] about to call analyze for video_id:{video_id} brand:{brand}")
        result = self.analyze_video(
            video_id=video_id,
            brand=brand,
            source_url=youtube_url or video_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 4) Cache analysis envelope
        if yt_id and self._redis:
            key = _redis_key_analysis(self.config.redis_prefix, yt_id, brand)
            ok = _redis_set_json(self._redis, key, result.model_dump(mode="json"))
            print(
                f"[cache] {'stored' if ok else 'FAILED to store'} analysis for yt:{yt_id} brand:{brand}"
            )

        return result

    # ---- Index helpers ----------------------------------------------------
    def _ensure_index(self) -> str:
        if self.config.index_id:
            return self.config.index_id
        # Try resolve by name
        for idx in self._client.indexes.list(index_name=self.config.index_name):
            if getattr(idx, "index_name", None) == self.config.index_name:
                self.config.index_id = getattr(idx, "id", None)
                if not self.config.index_id:
                    raise RuntimeError("Unable to resolve index id from SDK response.")
                return self.config.index_id
        # Create if not exists
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
                raise RuntimeError("Index creation succeeded but id missing.")
            return self.config.index_id
        except Exception:
            for idx in self._client.indexes.list(index_name=self.config.index_name):
                if getattr(idx, "index_name", None) == self.config.index_name:
                    self.config.index_id = getattr(idx, "id", None)
                    if self.config.index_id:
                        return self.config.index_id
            raise

    # ---- Ingest helpers ---------------------------------------------------
    def _ingest_from_url(
        self, index_id: str, url: str, *, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        print(f"[ingest] Received metadata: {metadata} (type: {type(metadata)})")
        video_url = url
        if _is_youtube_url(url):
            # Try RapidAPI resolver first
            try:
                from .yt_rapidapi_dl import resolve_youtube_direct_url
            except Exception:
                resolve_youtube_direct_url = None  # type: ignore
            direct = None
            if resolve_youtube_direct_url is not None:
                direct = resolve_youtube_direct_url(url)
            if direct:
                video_url = direct
                print(f"[ingest] resolved direct YouTube URL")

        try:
            print(f"[ingest] creating tasks.create with video_url")
            # Handle metadata serialization more robustly
            user_metadata = "{}"  # Default to empty JSON object instead of None
            if metadata:
                try:
                    # Ensure metadata is a proper dict and serialize with strict JSON
                    if not isinstance(metadata, dict):
                        print(
                            f"[ingest] Warning: metadata is not a dict, using empty object: {type(metadata)}"
                        )
                        user_metadata = "{}"
                    else:
                        user_metadata = json.dumps(
                            metadata, ensure_ascii=False, separators=(",", ":")
                        )
                        print(f"[ingest] Serialized metadata: {user_metadata}")
                        # Validate the JSON is actually valid
                        json.loads(user_metadata)
                except (TypeError, ValueError, json.JSONDecodeError) as e:
                    print(
                        f"[ingest] Warning: Failed to serialize metadata: {e}, using empty object"
                    )
                    user_metadata = "{}"

            task = self._client.tasks.create(
                index_id=index_id,
                video_url=video_url,
                user_metadata=user_metadata,
            )
            task_id = getattr(task, "id", None) or getattr(task, "_id", None)
            print(f"[ingest] upload by URL accepted; task_id:{task_id}")
        except Exception as e:
            # Fallback to local download for YouTube
            if _is_youtube_url(url) and self.config.allow_youtube_download_fallback:
                temp_path = _download_youtube_to_temp(url)
                if not temp_path:
                    raise RuntimeError(
                        "Direct YouTube URL not accepted and yt_dlp fallback failed."
                    ) from e
                try:
                    print(f"[ingest] uploading local file to Twelve Labs: {temp_path}")
                    with open(temp_path, "rb") as fh:
                        # Handle metadata serialization more robustly
                        user_metadata = (
                            "{}"  # Default to empty JSON object instead of None
                        )
                        if metadata:
                            try:
                                # Ensure metadata is a proper dict and serialize with strict JSON
                                if not isinstance(metadata, dict):
                                    print(
                                        f"[ingest] Warning: metadata is not a dict, using empty object: {type(metadata)}"
                                    )
                                    user_metadata = "{}"
                                else:
                                    user_metadata = json.dumps(
                                        metadata,
                                        ensure_ascii=False,
                                        separators=(",", ":"),
                                    )
                                    print(
                                        f"[ingest] Serialized metadata: {user_metadata}"
                                    )
                                    # Validate the JSON is actually valid
                                    json.loads(user_metadata)
                            except (TypeError, ValueError, json.JSONDecodeError) as e:
                                print(
                                    f"[ingest] Warning: Failed to serialize metadata: {e}, using empty object"
                                )
                                user_metadata = "{}"

                        task = self._client.tasks.create(
                            index_id=index_id,
                            video_file=fh,
                            user_metadata=user_metadata,
                        )
                    task_id = getattr(task, "id", None) or getattr(task, "_id", None)
                    print(f"[ingest] upload completed; task_id:{task_id}")
                finally:
                    try:
                        os.remove(temp_path)
                        print(f"[ingest] cleaned up temp file")
                    except Exception:
                        pass
            else:
                raise
        task_id = getattr(task, "id", None) or getattr(task, "_id", None)
        if not task_id:
            raise RuntimeError("Task creation response missing id.")
        print(f"[index] waiting for task {task_id} to complete")
        done = self._wait_for_task(task_id)
        if getattr(done, "status", None) != "ready":
            raise RuntimeError(
                f"Indexing failed: status={getattr(done, 'status', None)}"
            )
        video_id = getattr(done, "video_id", None)
        if not video_id:
            raise RuntimeError("Indexing completed but video_id missing in response.")
        print(f"[index] task ready; video_id:{video_id}")
        return video_id

    def _wait_for_task(self, task_id: str):
        import time

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
        import time

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


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Analyze a video for brand presence. Accepts an existing video_id or a URL "
            "(YouTube or direct). If a URL is provided, the service ingests then analyzes."
        )
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--video-id", help="Existing video ID in the Twelve Labs index")
    src.add_argument("--youtube-url", help="YouTube URL to ingest then analyze")
    src.add_argument("--video-url", help="Direct video URL to ingest then analyze")
    parser.add_argument("--brand", required=True, help="Brand name to detect")
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Sampling temperature (default 0.2)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=None, help="Maximum tokens for generation"
    )
    args = parser.parse_args()

    analyzer = TwelveLabsBrandAnalyzer.from_env()
    if args.video_id:
        res = analyzer.analyze_video(
            video_id=args.video_id,
            brand=args.brand,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    else:
        res = analyzer.analyze(
            brand=args.brand,
            youtube_url=args.youtube_url,
            video_url=args.video_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    # Print the full envelope as JSON for CLI/HTTP consumption
    print(res.model_dump_json(ensure_ascii=False))


if __name__ == "__main__":
    _cli()


# ---- Local helpers ---------------------------------------------------------
def _is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        return host.endswith("youtube.com") or host.endswith("youtu.be")
    except Exception:
        return False


def _extract_youtube_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""
        # youtu.be/<id>
        if host.endswith("youtu.be"):
            vid = path.lstrip("/").split("/")[0]
            return vid or None
        if host.endswith("youtube.com"):
            # Handle common path-based forms first (shorts, embed, live)
            # - /shorts/<id>
            # - /embed/<id>
            # - /live/<id>
            # - /watch?v=<id>
            segments = [s for s in path.split("/") if s]
            if segments:
                head = segments[0]
                if head in {"shorts", "embed", "live"} and len(segments) >= 2:
                    vid = segments[1]
                    # strip any trailing extra segmenting or .
                    vid = vid.split("?")[0].split("&")[0]
                    return vid or None
            # Fallback to query param v
            query = parsed.query or ""
            for part in query.split("&"):
                if not part:
                    continue
                k, _, v = part.partition("=")
                if k == "v" and v:
                    return v
    except Exception:
        return None
    return None


def _download_youtube_to_temp(url: str) -> Optional[str]:
    """
    Download a YouTube video to a temporary file using yt_dlp and return its path.
    Caller is responsible for deletion.
    """
    import tempfile

    try:
        import yt_dlp  # type: ignore
    except Exception:
        return None

    outtmpl = os.path.join(tempfile.gettempdir(), "twelvelabs-%(id)s.%(ext)s")
    ydl_opts: Dict[str, Any] = {
        "quiet": True,
        "format": "mp4/best",
        "noplaylist": True,
        "outtmpl": outtmpl,
    }
    # Optional cookies from a local browser (e.g., "chrome", "brave", "edge", "firefox")
    browser = os.getenv("YT_DLP_COOKIES_FROM_BROWSER")
    if browser:
        ydl_opts["cookiesfrombrowser"] = browser
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if isinstance(info, dict):
                path = ydl.prepare_filename(info)
                try:
                    size = os.path.getsize(path)
                except Exception:
                    size = -1
                print(f"[download] completed YouTube download: {path} ({size} bytes)")
                return path
    except Exception:
        return None
    return None


# ---- Redis helpers ---------------------------------------------------------
def _init_redis(redis_url: Optional[str]):
    """
    Initialize a Redis-like client.

    Priority:
    1) Upstash SDK (upstash-redis) via UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN
    2) Upstash REST fallback (requests)
    3) redis-py from REDIS_URL (or provided redis_url) or localhost fallback
    Returns an object supporting `.get(key)` and `.set(key, value)` with
    decoded string responses, or None if no backend is reachable.
    """
    # 1) Upstash SDK (preferred)
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if rest_url and rest_token:
        try:
            from upstash_redis import Redis as _UpstashRedis  # type: ignore

            client = _UpstashRedis(url=rest_url, token=rest_token)
            # liveness check: real round-trip
            try:
                probe_key = "__ba_probe__"
                client.set(probe_key, "1")
                if client.get(probe_key) == "1":
                    print("[redis] using Upstash SDK client")
                    return client
            except Exception:
                pass
        except Exception:
            pass

    # 2) Upstash REST (without SDK)
    if rest_url and rest_token:
        try:
            import requests  # noqa: F401

            class _UpstashRESTClient:
                def __init__(self, base_url: str, token: str):
                    self._url = base_url.rstrip("/")
                    self._token = token

                def _cmd(self, *parts):
                    try:
                        import requests

                        resp = requests.post(
                            f"{self._url}/pipeline",
                            headers={
                                "Authorization": f"Bearer {self._token}",
                                "Content-Type": "application/json",
                            },
                            json={"commands": [list(parts)]},
                            timeout=3.0,
                        )
                        if resp.status_code != 200:
                            return None
                        data = resp.json()
                        if isinstance(data, list) and data:
                            item = data[0]
                            if isinstance(item, dict):
                                # {'result': value} or {'error': '...'}
                                if "error" in item:
                                    return None
                                return item.get("result")
                        return None
                    except Exception:
                        return None

                def get(self, key: str):
                    res = self._cmd("GET", key)
                    return res if isinstance(res, str) else None

                def set(self, key: str, value: str):
                    res = self._cmd("SET", key, value)
                    return isinstance(res, str) and res.upper() == "OK"

            client = _UpstashRESTClient(rest_url, rest_token)
            # Quick liveness check with round-trip
            probe_key = "__ba_probe__"
            if client.set(probe_key, "1") and client.get(probe_key) == "1":
                print("[redis] using Upstash REST client")
                return client
        except Exception:
            pass

    # 3) redis-py
    if not redis_url:
        redis_url = os.getenv("REDIS_URL")
    try:
        import redis  # type: ignore

        kwargs = dict(
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
            health_check_interval=0,
            retry_on_timeout=False,
        )
        # Upstash via redis protocol requires TLS (rediss://)
        if redis_url and "upstash.io" in redis_url and redis_url.startswith("redis://"):
            redis_url = "rediss://" + redis_url[len("redis://") :]
        client = (
            redis.Redis.from_url(redis_url, **kwargs)
            if redis_url
            else redis.Redis(host="127.0.0.1", port=6379, db=0, **kwargs)
        )
        try:
            client.ping()
            print("[redis] using redis-py client")
        except Exception:
            return None
        return client
    except Exception:
        return None


def _brand_key(brand: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", brand.lower()).strip("_")


def _redis_key_video_map(prefix: str, yt_id: str) -> str:
    return f"{prefix}{yt_id}:tl_video_id"


def _redis_key_analysis(prefix: str, yt_id: str, brand: str) -> str:
    return f"{prefix}{yt_id}:analysis:{_brand_key(brand)}"


def _redis_get_text(r, key: str) -> Optional[str]:
    try:
        return r.get(key)
    except Exception:
        return None


def _redis_set_text(r, key: str, value: str) -> bool:
    try:
        res = r.set(key, value)
        if isinstance(res, bool):
            return res
        if isinstance(res, str):
            return res.upper() == "OK"
        return True if res is not None else False
    except Exception:
        return False


def _redis_get_json(r, key: str) -> Optional[Dict[str, Any]]:
    try:
        s = r.get(key)
        if not s:
            return None
        return json.loads(s)
    except Exception:
        return None


def _redis_set_json(r, key: str, value: Dict[str, Any]) -> bool:
    try:
        s = json.dumps(value, ensure_ascii=False)
        res = r.set(key, s)
        if isinstance(res, bool):
            return res
        if isinstance(res, str):
            return res.upper() == "OK"
        return True if res is not None else False
    except Exception:
        return False
