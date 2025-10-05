"""
FastAPI server exposing TwelveLabs brand analysis with ingest.

Endpoints
- GET /health    → health check
- POST /analyze  → Analyze a video by brand (video_id or URL)

Run locally
  uvicorn service.api:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from .twelvelabs_analyze_brand import (
    TwelveLabsBrandAnalyzer,
    _extract_youtube_id,
    _is_youtube_url,
    _redis_key_analysis,
    _redis_key_video_map,
)
from .brand_analysis_models import BrandAnalysisResult


class AnalyzeRequest(BaseModel):
    brand: str = Field(..., description="Brand name to detect")
    video_id: Optional[str] = Field(
        default=None, description="Existing TwelveLabs video id (if already indexed)"
    )
    youtube_url: Optional[str] = Field(
        default=None, description="YouTube URL to ingest then analyze"
    )
    video_url: Optional[str] = Field(
        default=None, description="Direct video URL to ingest then analyze"
    )
    temperature: Optional[float] = Field(
        default=None, description="Sampling temperature (defaults to 0.2)"
    )
    max_tokens: Optional[int] = Field(
        default=None, description="Max tokens; let API default if omitted"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata passed to ingest"
    )

    @model_validator(mode="after")
    def _check_source(self) -> "AnalyzeRequest":
        if not self.video_id and not (self.youtube_url or self.video_url):
            raise ValueError("Provide either video_id or youtube_url/video_url")
        return self


app = FastAPI(title="Brand Analysis API", version="1.0.0")

# CORS for frontend integration
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=BrandAnalysisResult)
def analyze(req: AnalyzeRequest) -> BrandAnalysisResult:
    try:
        analyzer = TwelveLabsBrandAnalyzer.from_env()
    except Exception as e:  # env/config error
        raise HTTPException(status_code=500, detail=str(e))

    try:
        res = analyzer.analyze(
            brand=req.brand,
            video_id=req.video_id,
            youtube_url=req.youtube_url,
            video_url=req.video_url,
            metadata=req.metadata,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Surface upstream errors with a generic 500; details captured client-side
        raise HTTPException(status_code=500, detail=str(e))


class CacheStatusResponse(BaseModel):
    cache_enabled: bool
    brand: Optional[str] = None
    youtube_id: Optional[str] = None
    mapping_key: Optional[str] = None
    mapping_video_id: Optional[str] = None
    analysis_key: Optional[str] = None
    has_mapping: bool = False
    has_analysis: bool = False


@app.get("/cache_status", response_model=CacheStatusResponse)
def cache_status(
    brand: Optional[str] = None,
    youtube_url: Optional[str] = None,
    video_url: Optional[str] = None,
) -> CacheStatusResponse:
    """
    Inspect Redis for cached data related to a YouTube URL and brand.

    - If a YouTube URL (or a video_url that is a YouTube link) is provided, returns
      whether a URL→video_id mapping exists and whether a brand-specific analysis
      envelope is cached.
    - If caching is disabled/unavailable, returns `cache_enabled=false`.
    """
    try:
        analyzer = TwelveLabsBrandAnalyzer.from_env()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    r = getattr(analyzer, "_redis", None)
    enabled = bool(r)

    yt_id: Optional[str] = None
    if youtube_url:
        yt_id = _extract_youtube_id(youtube_url)
    elif video_url and _is_youtube_url(video_url):
        yt_id = _extract_youtube_id(video_url)

    resp = CacheStatusResponse(
        cache_enabled=enabled,
        brand=brand,
        youtube_id=yt_id,
    )

    if not enabled or not yt_id:
        return resp

    # Mapping key check
    map_key = _redis_key_video_map(analyzer.config.redis_prefix, yt_id)
    resp.mapping_key = map_key
    try:
        mapped = r.get(map_key)  # type: ignore[attr-defined]
    except Exception:
        mapped = None
    if isinstance(mapped, bytes):
        try:
            mapped = mapped.decode("utf-8")
        except Exception:
            mapped = None
    resp.mapping_video_id = mapped if isinstance(mapped, str) and mapped else None
    resp.has_mapping = resp.mapping_video_id is not None

    # Analysis key check (brand-specific)
    if brand:
        analysis_key = _redis_key_analysis(analyzer.config.redis_prefix, yt_id, brand)
        resp.analysis_key = analysis_key
        try:
            analysis_json = r.get(analysis_key)  # type: ignore[attr-defined]
        except Exception:
            analysis_json = None
        if isinstance(analysis_json, (bytes, bytearray)):
            try:
                analysis_json = analysis_json.decode("utf-8")
            except Exception:
                analysis_json = None
        resp.has_analysis = bool(analysis_json)

    return resp


@app.head("/analysis")
def analysis_head(
    brand: Optional[str] = None,
    youtube_url: Optional[str] = None,
    video_url: Optional[str] = None,
) -> Response:
    """
    Fast existence check for cached analysis/mapping.

    - 200 if analysis exists for (yt_id, brand)
    - 404 if analysis not present (or brand missing)
    Response headers include quick diagnostics for UI branching.
    """
    try:
        analyzer = TwelveLabsBrandAnalyzer.from_env()
    except Exception as e:
        # For HEAD, surface as 503 to signal infra issue without a body
        return Response(status_code=503)

    r = getattr(analyzer, "_redis", None)
    headers: Dict[str, str] = {}
    headers["X-Cache-Enabled"] = "true" if r else "false"

    yt_id: Optional[str] = None
    if youtube_url:
        yt_id = _extract_youtube_id(youtube_url)
    elif video_url and _is_youtube_url(video_url):
        yt_id = _extract_youtube_id(video_url)

    headers["X-YouTube-Id"] = yt_id or ""

    has_mapping = False
    has_analysis = False
    if r and yt_id:
        try:
            map_key = _redis_key_video_map(analyzer.config.redis_prefix, yt_id)
            mapped = r.get(map_key)  # type: ignore[attr-defined]
            if isinstance(mapped, (bytes, bytearray)):
                try:
                    mapped = mapped.decode("utf-8")
                except Exception:
                    mapped = None
            has_mapping = bool(mapped)
        except Exception:
            has_mapping = False
        if brand:
            try:
                akey = _redis_key_analysis(analyzer.config.redis_prefix, yt_id, brand)
                aval = r.get(akey)  # type: ignore[attr-defined]
                has_analysis = bool(aval)
            except Exception:
                has_analysis = False

    headers["X-Has-Mapping"] = "true" if has_mapping else "false"
    headers["X-Has-Analysis"] = "true" if has_analysis else "false"

    return Response(status_code=(200 if has_analysis else 404), headers=headers)


@app.post("/analysis", response_model=BrandAnalysisResult)
def analysis_post(req: AnalyzeRequest) -> BrandAnalysisResult:
    """
    Idempotent upsert: returns cached analysis for the video/brand if present;
    otherwise ingests (if needed), analyzes, caches, and returns the result.
    """
    try:
        analyzer = TwelveLabsBrandAnalyzer.from_env()
    except Exception as e:  # env/config error
        raise HTTPException(status_code=500, detail=str(e))

    try:
        return analyzer.analyze(
            brand=req.brand,
            video_id=req.video_id,
            youtube_url=req.youtube_url,
            video_url=req.video_url,
            metadata=req.metadata,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "service.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
