from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load service env (index id, keys, RapidAPI, etc.). Non-fatal if missing.
load_dotenv("service/.env")

from service.twelvelabs_summary import TwelveLabsSummarizer  # noqa: E402


app = FastAPI(title="Swipe Service API", version="0.1.0")


class SummarizeRequest(BaseModel):
    youtube_url: Optional[str] = None
    video_url: Optional[str] = None
    style: Optional[str] = None
    language: Optional[str] = None
    allow_download: Optional[bool] = None  # override env fallback per-request

@app.post("/summarize")
def summarize(req: SummarizeRequest) -> dict:
    url = req.youtube_url or req.video_url
    if not url:
        raise HTTPException(status_code=400, detail="Provide youtube_url or video_url")

    try:
        summarizer = TwelveLabsSummarizer.from_env()
        if req.allow_download is not None:
            summarizer.config.allow_youtube_download_fallback = bool(req.allow_download)
        result = summarizer.summarize_youtube(
            youtube_url=url,
            style=req.style,
            language=req.language,
        )
        return result
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apis.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
