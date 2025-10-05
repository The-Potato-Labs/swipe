from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load service env (index id, keys, RapidAPI, etc.). Non-fatal if missing.
load_dotenv("service/.env")

from service.twelvelabs_summary import TwelveLabsSummarizer  # noqa: E402
from service.cloudglue_summary import CloudglueSummarizer  # noqa: E402
from service.twelvelabs_analyze_brand import TwelveLabsBrandAnalyzer  # noqa: E402
from service.brand_analysis_models import BrandAnalysisResult  # noqa: E402


app = FastAPI(title="Swipe Service API", version="0.1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SummarizeRequest(BaseModel):
    youtube_url: Optional[str] = None
    video_url: Optional[str] = None
    style: Optional[str] = None
    language: Optional[str] = None
    allow_download: Optional[bool] = None  # override env fallback per-request
    provider: Optional[str] = None  # "twelvelabs" | "cloudglue"


class AnalyzeRequest(BaseModel):
    brand: str
    video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    video_url: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    metadata: Optional[dict] = None

@app.post("/summarize")
def summarize(req: SummarizeRequest) -> dict:
    url = req.youtube_url or req.video_url
    if not url:
        raise HTTPException(status_code=400, detail="Provide youtube_url or video_url")

    provider = (req.provider or os.getenv("SUMMARY_PROVIDER") or "twelvelabs").lower()
    try:
        if provider == "cloudglue":
            cg = CloudglueSummarizer.from_env()
            result = cg.summarize_url(
                media_url=url,
                style=req.style,
                language=req.language,
                youtube=bool(req.youtube_url),
            )
            return result
        # default: Twelve Labs
        tw = TwelveLabsSummarizer.from_env()
        if req.allow_download is not None:
            tw.config.allow_youtube_download_fallback = bool(req.allow_download)
        result = tw.summarize_youtube(
            youtube_url=url,
            style=req.style,
            language=req.language,
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/analyze", response_model=BrandAnalysisResult)
def analyze(req: AnalyzeRequest) -> BrandAnalysisResult:
    """Analyze a video for brand mentions and sponsorship content."""
    if not req.video_id and not (req.youtube_url or req.video_url):
        raise HTTPException(status_code=400, detail="Provide either video_id or youtube_url/video_url")

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
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apis.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
