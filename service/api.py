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

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from .twelvelabs_analyze_brand import TwelveLabsBrandAnalyzer
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "service.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
