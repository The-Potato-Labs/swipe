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
import {
  Play,
  Eye,
  Mic,
  ShoppingBag,
  Target,
  Gift,
  AlertCircle,
  Zap,
  Monitor,
  MessageSquare,
} from "lucide-react";
import { analyzeVideo, BrandAnalysisResult } from "@/lib/services/analyze";
import { cn, getVideoId } from "@/lib/utils";

// Helper function to seek video to specific time
function seekToTime(seconds: number, sheetElement?: HTMLElement) {
  // Find the iframe within the specific sheet, not just any iframe on the page
  const iframe =
    sheetElement?.querySelector("iframe") || document.querySelector("iframe");
  if (!iframe) {
    console.log("No iframe found in sheet");
    return;
  }

  console.log("Current iframe src:", iframe.src);
  console.log("Seeking to:", seconds, "seconds");

  // Handle YouTube embeds
  if (iframe.src.includes("youtube.com")) {
    const videoIdMatch = iframe.src.match(/embed\/([^?]+)/);
    if (videoIdMatch) {
      const videoId = videoIdMatch[1];
      const newSrc = `https://www.youtube.com/embed/${videoId}?start=${Math.floor(
        seconds
      )}&autoplay=1`;
      console.log("Updating YouTube iframe to:", newSrc);
      iframe.src = newSrc;
      return;
    }
  }

  // Handle Vimeo embeds
  if (iframe.src.includes("vimeo.com")) {
    const videoIdMatch = iframe.src.match(/video\/(\d+)/);
    if (videoIdMatch) {
      const videoId = videoIdMatch[1];
      const newSrc = `https://player.vimeo.com/video/${videoId}?t=${Math.floor(
        seconds
      )}s&autoplay=1`;
      console.log("Updating Vimeo iframe to:", newSrc);
      iframe.src = newSrc;
      return;
    }
  }

  // Try postMessage as fallback for other players
  try {
    iframe.contentWindow?.postMessage(
      {
        event: "command",
        func: "seekTo",
        args: [seconds, true],
      },
      "*"
    );
    console.log("Sent postMessage seek command");
  } catch (error) {
    console.log("PostMessage failed:", error);
  }
}

// Helper function to convert HH:MM:SS to seconds
function timeToSeconds(timeStr: string): number {
  if (!timeStr || typeof timeStr !== "string") return 0;

  const parts = timeStr.split(":").map(Number);

  // Handle different timestamp formats
  if (parts.length === 2) {
    // MM:SS format
    return parts[0] * 60 + parts[1];
  } else if (parts.length === 3) {
    // HH:MM:SS format
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  } else if (parts.length === 1) {
    // Just seconds
    return parts[0];
  }

  return 0;
}

// Helper function to calculate duration between two timestamps
function calculateDuration(startTime: string, endTime: string): string {
  const startSeconds = timeToSeconds(startTime);
  const endSeconds = timeToSeconds(endTime);
  const durationSeconds = endSeconds - startSeconds;

  // Handle invalid durations
  if (isNaN(durationSeconds) || durationSeconds < 0) {
    return "0s";
  }

  if (durationSeconds < 60) {
    return `${Math.round(durationSeconds)}s`;
  } else if (durationSeconds < 3600) {
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = Math.round(durationSeconds % 60);
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(durationSeconds / 3600);
    const minutes = Math.floor((durationSeconds % 3600) / 60);
    const seconds = Math.round(durationSeconds % 60);
    let result = `${hours}h`;
    if (minutes > 0) result += ` ${minutes}m`;
    if (seconds > 0) result += ` ${seconds}s`;
    return result;
  }
}

// Helper function to get icon for mention type
function getMentionIcon(mentionType: string) {
  const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    sponsor_segment: Play,
    on_screen_element: Eye,
    verbal_mention: Mic,
    product_visual: ShoppingBag,
    product_demo: Monitor,
    comparison_section: Target,
    call_to_action: Zap,
    affiliate_disclosure: AlertCircle,
    giveaway_or_promo: Gift,
    end_screen: MessageSquare,
  };
  return iconMap[mentionType] || Eye;
}

// Helper function to get color for mention type
function getMentionColor(mentionType: string): string {
  const colorMap: Record<string, string> = {
    sponsor_segment: "bg-red-600/20 text-red-300",
    on_screen_element: "bg-blue-600/20 text-blue-300",
    verbal_mention: "bg-green-600/20 text-green-300",
    product_visual: "bg-purple-600/20 text-purple-300",
    product_demo: "bg-orange-600/20 text-orange-300",
    comparison_section: "bg-yellow-600/20 text-yellow-300",
    call_to_action: "bg-pink-600/20 text-pink-300",
    affiliate_disclosure: "bg-gray-600/20 text-gray-300",
    giveaway_or_promo: "bg-indigo-600/20 text-indigo-300",
    end_screen: "bg-teal-600/20 text-teal-300",
  };
  return colorMap[mentionType] || "bg-slate-600/20 text-slate-300";
}

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
    <Sheet
      open={open}
      onOpenChange={setOpen}
    >
      <SheetTrigger>{children}</SheetTrigger>
      <SheetContent
        className={cn(
          "gap-2 flex flex-col w-[600px] sm:w-[800px] sm:max-w-none",
          className
        )}
      >
        <SheetHeader className="flex-shrink-0">
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
        <div className="flex flex-col gap-4 px-4 text-sm overflow-y-auto flex-1">
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
                      <span
                        key={t}
                        className="border rounded-sm px-1.5 py-0.5"
                      >
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
                      <span
                        key={h}
                        className="border rounded-sm px-1.5 py-0.5"
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {result.data.chapters?.length > 0 && (
                <div className="flex flex-col gap-2">
                  <h3>Chapters</h3>
                  <div className="flex flex-col gap-1">
                    {result.data.chapters.map((chapter) => {
                      // Check if this chapter has any sponsor-related brand mentions
                      const hasSponsorMention =
                        result.data.brand_mentions?.some((mention) => {
                          // Check if mention type is sponsor-related
                          const isSponsorType =
                            mention.mention_type === "sponsor_segment" ||
                            mention.mention_type === "product_demo" ||
                            mention.mention_type === "call_to_action";

                          if (!isSponsorType) return false;

                          // Check if mention timestamp overlaps with chapter timestamp
                          const mentionStart = timeToSeconds(
                            mention.timestamps.start
                          );
                          const mentionEnd = timeToSeconds(
                            mention.timestamps.end
                          );
                          const chapterStart = timeToSeconds(
                            chapter.timestamps.start
                          );
                          const chapterEnd = timeToSeconds(
                            chapter.timestamps.end
                          );

                          // Check for overlap: mention starts within chapter or mention contains chapter
                          return (
                            (mentionStart >= chapterStart &&
                              mentionStart < chapterEnd) ||
                            (mentionEnd > chapterStart &&
                              mentionEnd <= chapterEnd) ||
                            (mentionStart <= chapterStart &&
                              mentionEnd >= chapterEnd)
                          );
                        });

                      return (
                        <div
                          key={chapter.id}
                          className="flex items-center justify-between p-2 border border-slate-700 rounded hover:bg-slate-800/30 transition-colors"
                        >
                          <div className="flex flex-col gap-1 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-slate-200">
                                {chapter.title}
                              </span>
                              {hasSponsorMention && (
                                <span className="text-xs px-2 py-1 bg-green-600/20 text-green-300 rounded">
                                  sponsor
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-slate-400">
                              {chapter.summary}
                            </span>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <button
                              className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded transition-colors"
                              onClick={(e) => {
                                const startSeconds = timeToSeconds(
                                  chapter.timestamps.start
                                );
                                // Find the sheet content element
                                const sheetContent = e.currentTarget.closest(
                                  '[data-slot="sheet-content"]'
                                );
                                seekToTime(
                                  startSeconds,
                                  sheetContent as HTMLElement
                                );
                              }}
                            >
                              {chapter.timestamps.start}
                            </button>
                            <span className="text-xs text-slate-500">
                              {calculateDuration(
                                chapter.timestamps.start,
                                chapter.timestamps.end
                              )}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {Array.isArray(result.data.brand_mentions) &&
                result.data.brand_mentions.length > 0 && (
                  <div className="flex flex-col gap-2">
                    <h3>Brand Mentions</h3>
                    <div className="flex flex-col gap-2">
                      {result.data.brand_mentions.map((mention) => {
                        const IconComponent = getMentionIcon(
                          mention.mention_type
                        );
                        const colorClass = getMentionColor(
                          mention.mention_type
                        );
                        const confidenceColor =
                          mention.confidence > 0.8
                            ? "bg-green-500"
                            : mention.confidence > 0.6
                            ? "bg-yellow-500"
                            : "bg-red-500";

                        return (
                          <div
                            key={mention.id}
                            className="border border-slate-700 rounded-md p-3 bg-slate-800/50"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <IconComponent className="w-4 h-4 text-slate-400" />
                                <span
                                  className={`text-xs px-2 py-1 ${colorClass} rounded`}
                                >
                                  {mention.mention_type.replace(/_/g, " ")}
                                </span>
                                {mention.subtype && (
                                  <span className="text-xs px-2 py-1 bg-slate-600/20 text-slate-300 rounded">
                                    {mention.subtype.replace(/_/g, " ")}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="flex flex-col items-end gap-1">
                                  <button
                                    className="text-xs px-2 py-1 bg-slate-700 hover:bg-slate-600 rounded transition-colors"
                                    onClick={(e) => {
                                      const startSeconds = timeToSeconds(
                                        mention.timestamps.start
                                      );
                                      // Find the sheet content element
                                      const sheetContent =
                                        e.currentTarget.closest(
                                          '[data-slot="sheet-content"]'
                                        );
                                      seekToTime(
                                        startSeconds,
                                        sheetContent as HTMLElement
                                      );
                                    }}
                                  >
                                    {mention.timestamps.start}
                                  </button>
                                  <span className="text-xs text-slate-500">
                                    {calculateDuration(
                                      mention.timestamps.start,
                                      mention.timestamps.end
                                    )}
                                  </span>
                                </div>
                                <div className="flex items-center gap-1">
                                  <div
                                    className={`w-2 h-2 rounded-full ${confidenceColor}`}
                                  ></div>
                                  <span className="text-xs text-slate-400">
                                    {Math.round(mention.confidence * 100)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                            <p className="text-sm text-slate-300 mb-1">
                              {mention.description}
                            </p>
                            {mention.spoken_quote && (
                              <p className="text-xs text-slate-400 italic">
                                "{mention.spoken_quote}"
                              </p>
                            )}
                            {mention.text && (
                              <p className="text-xs text-slate-500">
                                On-screen: {mention.text}
                              </p>
                            )}
                            {mention.placement && (
                              <p className="text-xs text-slate-500">
                                Placement: {mention.placement}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
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
