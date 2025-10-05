import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// convert youtube url to an embed url
export function convertYoutubeUrlToEmbedUrl(url: string) {
  const youtubeRegex =
    /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
  const match = url.match(youtubeRegex);
  if (match) {
    return `https://www.youtube.com/embed/${match[1]}`;
  }
  return url;
}

// format text by removing underscores and converting to title case
export function formatTextToTitleCase(text: string | undefined | null): string {
  if (!text) return "";
  return text.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}
