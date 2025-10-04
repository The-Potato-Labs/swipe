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
    result = analyzer.analyze_video(
        video_id="<VIDEO_ID>",
        brand="Nike",
    )
    print(result["json"])  # parsed JSON (dict)

To run as a script:
    python -m service.twelvelabs_analyze_brand --video-id <VIDEO_ID> --brand "Nike"

Requirements:
- twelvelabs==1.x (already in service/requirements.txt)
- Optional: python-dotenv for .env loading (same as other service modules)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


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


from .brand_analysis_models import BrandAnalysisOutput


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
    "1. Segment the video into 3–8 meaningful chapters; fill id, title, summary, timestamps.\n"
    "2. List all brand mentions across the entire video in brand_mentions.\n"
    "3. For sponsor/ad reads (video section covering the brand), set mention_type=\"sponsor_segment\" and provide a detailed description with start/end.\n"
    "4. For on-screen elements (brand name, logo, website, QR, coupon), set mention_type=\"on_screen_element\" and subtype accordingly; include placement and start/end.\n"
    "5. Also capture verbal_mention, product_visual, product_demo, comparison_section, call_to_action (\"use code...\"), affiliate_disclosure (\"this video is sponsored by...\"), giveaway_or_promo, and end_screen references.\n"
    "6. If none detected, return an empty array for brand_mentions.\n"
    "7. If a mention is not tied to a single chapter, omit chapter_id.\n"
    "8. Add main topics and 3–8 concise hashtags that reflect the video’s themes.\n"
    "9. Output strictly valid JSON (no markdown, no commentary).\n"
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
    # optional defaults for generation
    temperature: float = 0.2
    max_tokens: Optional[int] = None  # let the API default unless specified


class TwelveLabsBrandAnalyzer:
    def __init__(self, config: TwelveLabsAnalyzeConfig):
        self.config = config
        TwelveLabs, ResponseFormat = _require_sdk()
        self._client = TwelveLabs(api_key=self.config.api_key)
        self._ResponseFormat = ResponseFormat

    @classmethod
    def from_env(cls) -> "TwelveLabsBrandAnalyzer":
        # Keep consistent with existing modules that use dotenv
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if not api_key:
            raise ValueError("Missing TWELVE_LABS_API_KEY. Set it in your environment.")
        cfg = TwelveLabsAnalyzeConfig(api_key=api_key)
        return cls(cfg)

    def _build_prompt(self, brand: str) -> str:
        # Generate JSON Schema from Pydantic models for inclusion in prompt
        schema = BrandAnalysisOutput.model_json_schema()
        schema_str = json.dumps(schema, ensure_ascii=False)
        return (
            PROMPT_TEMPLATE.replace("{brand}", brand)
            .replace("{json_schema}", schema_str)
        )

    def analyze_video(
        self,
        *,
        video_id: str,
        brand: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run Twelve Labs analyze on a single video with the brand-focused prompt.

        Returns a dict with:
        - video_id: the input video id
        - json: parsed JSON object (or None if parsing failed)
        - raw: the SDK response as dict (contains raw 'data' string)
        - prompt: the effective prompt (for auditability)
        """
        _, ResponseFormat = _require_sdk()
        prompt = self._build_prompt(brand)

        rf = ResponseFormat(type="json_schema", json_schema=BRAND_ANALYSIS_SCHEMA)
        resp = self._client.analyze(
            video_id=video_id,
            prompt=prompt,
            temperature=(temperature if temperature is not None else self.config.temperature),
            response_format=rf,
            max_tokens=(max_tokens if max_tokens is not None else self.config.max_tokens),
        )

        # Convert response into a stable dict form and parse JSON payload
        if hasattr(resp, "model_dump"):
            raw = resp.model_dump()
        else:  # pragma: no cover - fallback for unexpected SDK objects
            # Minimal attributes expected: id, data, finish_reason, usage
            raw = {k: getattr(resp, k, None) for k in ("id", "data", "finish_reason", "usage")}

        parsed: Optional[Dict[str, Any]] = None
        data = raw.get("data")
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
            except Exception:
                parsed = None

        return {
            "video_id": video_id,
            "prompt": prompt,
            "json": parsed,
            "raw": raw,
        }


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze a Twelve Labs-indexed video for brand presence, returning strict JSON."
    )
    parser.add_argument("--video-id", required=True, help="Video ID in the Twelve Labs index")
    parser.add_argument("--brand", required=True, help="Brand name to detect")
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature (default 0.2)")
    parser.add_argument("--max-tokens", type=int, default=None, help="Maximum tokens for generation")
    args = parser.parse_args()

    analyzer = TwelveLabsBrandAnalyzer.from_env()
    res = analyzer.analyze_video(
        video_id=args.video_id,
        brand=args.brand,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    # Print only the JSON payload if parsing succeeded; else print raw data field
    if res.get("json") is not None:
        print(json.dumps(res["json"], ensure_ascii=False))
    else:
        raw = res.get("raw") or {}
        data = raw.get("data")
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(raw, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
