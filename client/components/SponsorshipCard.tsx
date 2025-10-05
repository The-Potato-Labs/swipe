import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
  CardFooter,
} from "@/components/ui/card";
import { HeartIcon, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import SponsorshipSheet from "@/components/SponsorshipSheet";
import { convertYoutubeUrlToEmbedUrl, getYoutubeThumbnail } from "@/lib/utils";
import { useState } from "react";

interface SponsorshipCardProps {
  videoUrl: string;
  offset_seconds?: number;
  title: string;
  showCardTitle?: boolean;
  children: React.ReactNode;
  className?: string;
}

const SponsorshipCard: React.FC<SponsorshipCardProps> = ({
  videoUrl,
  offset_seconds,
  title,
  showCardTitle = true,
  children,
  className = "",
}) => {
  const [embedError, setEmbedError] = useState(false);
  const [showEmbed, setShowEmbed] = useState(false);

  // Convert YouTube URL to embed format
  const embedUrl = convertYoutubeUrlToEmbedUrl(videoUrl, offset_seconds);
  console.log("embed url : ", embedUrl);
  // Get YouTube thumbnail URL
  const thumbnailUrl = getYoutubeThumbnail(videoUrl);

  return (
    <Card
      className={`h-full rounded-md overflow-hidden ${
        showCardTitle ? "py-2.5" : "pt-0 pb-2.5"
      } gap-3 ${className}`}
    >
      {showCardTitle && (
        <CardHeader className="pl-4 pr-2 py-0">
          <CardTitle className="mt-3">{title}</CardTitle>
        </CardHeader>
      )}
      {/* video player */}
      <CardContent className="p-0">
        <div className="relative w-full h-0 pb-[56.25%] overflow-hidden">
          {!embedError && showEmbed ? (
            <iframe
              src={embedUrl}
              title={title}
              className="absolute top-0 left-0 w-full h-full border-0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              onError={() => setEmbedError(true)}
            />
          ) : (
            <div className="absolute top-0 left-0 w-full h-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
              {thumbnailUrl ? (
                <div
                  className="relative w-full h-full group cursor-pointer"
                  onClick={() => setShowEmbed(true)}
                >
                  <img
                    src={thumbnailUrl}
                    alt={title}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                  <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="bg-red-600 rounded-full p-4">
                      <Play className="w-8 h-8 text-white" />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center p-4">
                  <Play className="w-12 h-12 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm text-gray-500">Click to play video</p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-2"
                    onClick={() => window.open(videoUrl, "_blank")}
                  >
                    Open in YouTube
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
      {/* video info */}
      <CardContent className="py-2 px-4">
        {/* reason why it's a match */}
        {/* */}
        <div className="flex flex-col gap-2">
          <CardDescription>{children}</CardDescription>
        </div>
      </CardContent>
      <CardFooter className="pb-3 px-4">
        <SponsorshipSheet
          videoUrl={embedUrl}
          title={title}
          sheetChildren={children}
        >
          <span className="flex items-center gap-2 text-sm border px-2 py-1.5 rounded-sm hover:bg-white/10">
            <Sparkles className="w-4 h-4 fill-slate-400 stroke-transparent" />
            Get Insights
          </span>
        </SponsorshipSheet>
      </CardFooter>
    </Card>
  );
};

export default SponsorshipCard;
