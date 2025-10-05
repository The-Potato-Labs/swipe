import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Play, Sparkles } from "lucide-react";
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
  const [showEmbed, setShowEmbed] = useState(true);

  // Convert YouTube URL to embed format
  const watchUrl = videoUrl;
  const embedUrl = convertYoutubeUrlToEmbedUrl(watchUrl, offset_seconds);
  console.log("embed url : ", embedUrl);
  // Get YouTube thumbnail URL
  const thumbnailUrl = getYoutubeThumbnail(watchUrl);

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
                <button
                  onClick={() => window.open(watchUrl, "_blank")}
                  className="hover:bg-white/5 text-center p-4 w-full h-full flex flex-col gap-3 items-center justify-center hover:text-white hover:cursor-pointer"
                >
                  <div className="bg-red-600 rounded-full p-4">
                    <Play className="w-8 h-8 text-white" />
                  </div>
                  <p className="text-sm">View on YouTube</p>
                </button>
              )}
            </div>
          )}
        </div>
      </CardContent>
      {/* video info */}
      <CardContent className="pt-1.5 pb-1 px-4 flex flex-col gap-2 grow">
        {/* reason why it's a match */}
        <CardDescription>{children}</CardDescription>
      </CardContent>
      <CardFooter className="pb-3 px-4">
        <SponsorshipSheet
          videoUrl={embedUrl}
          sourceUrl={watchUrl}
          brand={title}
          title={title}
          sheetChildren={children}
        >
          <span className="flex items-center gap-2 text-sm border px-2 py-1.5 rounded-sm hover:bg-white/10">
            <Sparkles className="w-4 h-4 fill-slate-400 stroke-transparent" />
            Analyze Video
          </span>
        </SponsorshipSheet>
      </CardFooter>
    </Card>
  );
};

export default SponsorshipCard;
