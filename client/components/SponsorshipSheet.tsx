"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { analyzeVideo, BrandAnalysisResult } from "@/lib/services/analyze";
import { cn, getVideoId } from "@/lib/utils";

interface SponsorshipSheetProps {
  videoUrl: string; // embed URL for iframe
  sourceUrl?: string; // original YouTube or direct URL for analysis
  brand?: string; // brand to analyze; defaults to `title`
  title: string;
  children: React.ReactNode;
  sheetChildren: React.ReactNode;
  className?: string;
}

// placeholder removed: content now populated from analysis response

const SponsorshipSheet: React.FC<SponsorshipSheetProps> = ({
  videoUrl,
  sourceUrl,
  brand,
  title,
  children,
  sheetChildren,
  className,
}) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BrandAnalysisResult | null>(null);
  const hasRequestedRef = useRef(false);

  const effectiveBrand = useMemo(() => brand || title, [brand, title]);

  const triggerAnalyze = useCallback(async () => {
    if (hasRequestedRef.current) return; // avoid duplicate calls per open session
    if (!effectiveBrand || !(sourceUrl && sourceUrl.length > 0)) return;
    setLoading(true);
    setError(null);
    try {
      const videoId = getVideoId(sourceUrl);
      const res = await analyzeVideo(
        videoId
          ? { brand: effectiveBrand, youtube_url: sourceUrl }
          : { brand: effectiveBrand, video_url: sourceUrl }
      );
      setResult(res);
      hasRequestedRef.current = true;
    } catch (e: any) {
      setError(e?.message || "Failed to analyze");
    } finally {
      setLoading(false);
    }
  }, [effectiveBrand, sourceUrl]);

  useEffect(() => {
    if (open) {
      void triggerAnalyze();
    }
  }, [open, triggerAnalyze]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger>{children}</SheetTrigger>
      <SheetContent className={cn("gap-2", className)}>
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription className="mt-4 px-0">
            <span className="aspect-video w-full">
              <iframe
                src={videoUrl}
                title={title}
                className="w-full h-full rounded-md"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </span>
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4 text-sm">
          {/* same as content from card */}
          {sheetChildren}
          {/* analysis results */}
          {loading && (
            <div className="flex flex-row items-center gap-2">
              <Spinner className="w-4 h-4 text-slate-400" />{" "}
              <p>Analyzing video...</p>
            </div>
          )}
          {result && (
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <h3>Summary</h3>
                <p className="text-sm text-slate-400">{result.data.summary}</p>
              </div>
              {result.data.topics?.length > 0 && (
                <div className="flex flex-col gap-1">
                  <h3>Topics</h3>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                    {result.data.topics.map((t) => (
                      <span key={t} className="border rounded-sm px-1.5 py-0.5">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {result.data.hashtags?.length > 0 && (
                <div className="flex flex-col gap-1">
                  <h3>Hashtags</h3>
                  <div className="flex flex-wrap gap-2 text-xs text-slate-300">
                    {result.data.hashtags.map((h) => (
                      <span key={h} className="border rounded-sm px-1.5 py-0.5">
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {Array.isArray(result.data.brand_mentions) && (
                <div className="flex flex-col gap-1">
                  <h3>Brand Mentions</h3>
                  <p className="text-xs text-slate-400">
                    {result.data.brand_mentions.length} mentions detected
                  </p>
                </div>
              )}
            </div>
          )}
          {error && <div className="text-red-500">{error}</div>}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default SponsorshipSheet;
