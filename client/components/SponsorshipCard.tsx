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
import { HeartIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import SponsorshipSheet from "@/components/SponsorshipSheet";

interface SponsorshipCardProps {
  videoUrl: string;
  title: string;
  description: string;
  className?: string;
}

const SponsorshipCard: React.FC<SponsorshipCardProps> = ({
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
  const relevance = 0.95;

  return (
    <Card className={`py-2.5 gap-3 ${className}`}>
      <CardHeader className="pl-4 pr-2 py-0">
        <CardTitle className="mt-3">{title}</CardTitle>
        <CardAction>
          <Button
            variant="ghost"
            size="icon"
          >
            <HeartIcon className="w-4 h-4" />
          </Button>
        </CardAction>
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
      <CardContent className="py-2 px-4">
        {/* reason why it's a match */}
        {/* */}
        <div className="flex flex-col gap-2">
          <CardDescription className="font-semibold text-white">
            Relevance: {relevance}
          </CardDescription>
          <CardDescription>{description}</CardDescription>
        </div>
      </CardContent>
      <CardFooter className="pb-3 px-4">
        <SponsorshipSheet
          videoUrl={videoUrl}
          title={title}
          description={description}
        >
          <Button
            variant="outline"
            size="sm"
          >
            View Details
          </Button>
        </SponsorshipSheet>
      </CardFooter>
    </Card>
  );
};

export default SponsorshipCard;
