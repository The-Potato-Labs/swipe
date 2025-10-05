"""
Pydantic models for brand-focused video analysis output.

These models serve two purposes:
- Provide a strong-typed structure the service can use to validate and parse
  results from Twelve Labs analyze endpoint.
- Generate a JSON Schema (via Pydantic v2) to embed into prompts given to the
  model, so the structure is explicit and machine-parseable.

Note: The Twelve Labs `response_format` currently accepts only a subset of JSON
Schema. We therefore still use a minimal hand-authored schema for the API call,
while this Pydantic schema is used for prompt guidance and local validation.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class Timestamps(BaseModel):
    start: str = Field(description="Start time HH:MM:SS")
    end: str = Field(description="End time HH:MM:SS")


class Chapter(BaseModel):
    id: str = Field(description="Chapter id like ch_001")
    title: str
    summary: str
    timestamps: Timestamps


MentionType = Literal[
    "sponsor_segment",
    "on_screen_element",
    "verbal_mention",
    "product_visual",
    "product_demo",
    "comparison_section",
    "call_to_action",
    "affiliate_disclosure",
    "giveaway_or_promo",
    "end_screen",
]

OnScreenSubtype = Literal[
    "brand_name_text",
    "logo",
    "website",
    "qr_code",
    "coupon_code",
    "lower_third",
    "banner_overlay",
    "card_overlay",
    "watermark",
]


class BrandMention(BaseModel):
    id: str = Field(description="Mention id like bm_001")
    mention_type: MentionType
    subtype: Optional[OnScreenSubtype] = Field(
        default=None, description="Subtype for on_screen_element; omit if N/A"
    )
    description: str = Field(description="What is said or shown about the brand")
    chapter_id: Optional[str] = Field(
        default=None,
        description="Chapter id if tied to a single chapter; omit if not",
    )
    timestamps: Timestamps
    placement: Optional[str] = Field(
        default=None,
        description="Visual placement for on-screen elements (e.g., lower-third left)",
    )
    text: Optional[str] = Field(default=None, description="Overlay/OCR text if any")
    spoken_quote: Optional[str] = Field(
        default=None, description="Short quote if verbally mentioned"
    )
    confidence: float = Field(description="0.0–1.0 confidence score")


class BrandAnalysisOutput(BaseModel):
    summary: str
    hashtags: List[str]
    topics: List[str]
    chapters: List[Chapter]
    brand_mentions: List[BrandMention]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None


class BrandAnalysisMeta(BaseModel):
    provider: str = Field(default="twelvelabs")
    brand: str
    video_id: str
    index_id: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime
    elapsed_ms: int
    schema_version: str = Field(default="brand_analysis.v1")
    schema_url: Optional[str] = None
    trace_id: Optional[str] = None


class BrandAnalysisResult(BaseModel):
    data: BrandAnalysisOutput
    meta: BrandAnalysisMeta
    errors: List[ErrorDetail] = Field(default_factory=list)
