import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card";
import { HeartIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VideoCardProps {
  videoUrl: string;
  title: string;
  description: string;
  className?: string;
}

const VideoCard: React.FC<VideoCardProps> = ({
  videoUrl,
  title,
  description,
  className = "",
}) => {
  // Convert YouTube URL to embed format
  const getEmbedUrl = (url: string): string => {
    // Handle different YouTube URL formats
    const youtubeRegex =
      /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(youtubeRegex);

    if (match) {
      return `https://www.youtube.com/embed/${match[1]}`;
    }

    // If it's already an embed URL, return as is
    if (url.includes("youtube.com/embed/")) {
      return url;
    }

    // For other video URLs, return the original URL
    return url;
  };

  const embedUrl = getEmbedUrl(videoUrl);

  return (
    <Card className={`py-5 gap-4 ${className}`}>
      <CardHeader>
        <CardTitle className="mt-2">{title}</CardTitle>
      </CardHeader>
      {/* video player */}
      <CardContent className="p-0">
        <div className="relative w-full h-0 pb-[56.25%] overflow-hidden">
          <iframe
            src={embedUrl}
            title={title}
            className="absolute top-0 left-0 w-full h-full border-0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      </CardContent>

      {/* video info */}
      <CardContent>
        <CardTitle className="text-base 2xl:text-lg font-semibold text-slate-900 dark:text-white mb-2">
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
        {/* relevance / how good of a match it is */}
        {/* reason */}
      </CardContent>
    </Card>
  );
};

export default VideoCard;
