const SERVICE_BASE =
  process.env.NEXT_PUBLIC_SERVICE_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type AnalyzeParams = {
  brand: string;
  youtube_url?: string;
  video_id?: string;
  video_url?: string;
  temperature?: number;
  max_tokens?: number;
  metadata?: Record<string, any>;
};

export type BrandAnalysisOutput = {
  summary: string;
  hashtags: string[];
  topics: string[];
  chapters: Array<{
    id: string;
    title: string;
    summary: string;
    timestamps: { start: string; end: string };
  }>;
  brand_mentions: Array<{
    id: string;
    mention_type: string;
    subtype?: string | null;
    description: string;
    chapter_id?: string | null;
    timestamps: { start: string; end: string };
    placement?: string | null;
    text?: string | null;
    spoken_quote?: string | null;
    confidence: number;
  }>;
};

export type BrandAnalysisMeta = {
  provider: string;
  brand: string;
  video_id: string;
  index_id?: string | null;
  source_url?: string | null;
  created_at: string;
  elapsed_ms: number;
  schema_version: string;
  schema_url?: string | null;
  trace_id?: string | null;
};

export type BrandAnalysisResult = {
  data: BrandAnalysisOutput;
  meta: BrandAnalysisMeta;
  errors: Array<{ code: string; message: string; details?: any }>;
};

export async function analyzeVideo(params: AnalyzeParams): Promise<BrandAnalysisResult> {
  const resp = await fetch(`${SERVICE_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Analyze failed: ${resp.status} ${text}`);
  }
  return (await resp.json()) as BrandAnalysisResult;
}

