import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// convert youtube url to an embed url
export function convertYoutubeUrlToEmbedUrl(url: string, offset: number = 0) {
  const videoId = getVideoId(url);
  if (videoId) {
    const embedUrl = `https://www.youtube.com/embed/${videoId}`;
    if (offset > 0) {
      return `${embedUrl}?start=${Math.floor(offset)}`;
    }
    return embedUrl;
  }
  return url;
}

// extract video ID from youtube url
export function getVideoId(url: string): string | null {
  const youtubeRegex =
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
  const match = url.match(youtubeRegex);
  return match ? match[1] : null;
}

// get youtube thumbnail url from video url
export function getYoutubeThumbnail(url: string): string | null {
  const videoId = getVideoId(url);
  return videoId
    ? `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`
    : null;
}

// convert text to title case (capitalize first letter of each word)
export function toTitleCase(text: string | undefined | null): string {
  if (!text) return "";
  return text.replace(/\b\w/g, (l) => l.toUpperCase());
}
