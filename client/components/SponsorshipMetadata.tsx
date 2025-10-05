"use client";

import Link from "next/link";
import { UserRound, Tag, Calendar, Locate } from "lucide-react";
import { Sponsorship } from "@/lib/models/sponsorship";
import { toTitleCase } from "@/lib/utils";

interface SponsorshipMetadataProps {
  sponsorship: Sponsorship;
}

export default function SponsorshipMetadata({
  sponsorship,
}: SponsorshipMetadataProps) {
  const { publication_name, publication_url, sponsor_type, published_date } =
    sponsorship;

  return (
    <div className="flex flex-wrap gap-4 text-slate-300">
      <div className="flex items-center gap-2">
        <UserRound className="w-4 h-4 text-slate-400" />
        <Link
          href={publication_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <span className="text-white">{publication_name}</span>
        </Link>
      </div>
      <div className="flex items-center gap-2">
        <Calendar className="w-4 h-4 text-slate-400" />
        <span>
          {published_date
            ? new Date(published_date).toLocaleDateString()
            : "--"}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Tag className="w-4 h-4 text-slate-400" />
        <span>{toTitleCase(formatSponsorType(sponsor_type))}</span>
      </div>
    </div>
  );
}

// format sponsor type - return "Ad" if sponsor type is "explicit_ad", otherwise return the sponsor type
function formatSponsorType(sponsor_type: string) {
  if (sponsor_type === "explicit_ad") {
    return "Ad";
  } else {
    return sponsor_type.replace(/_/g, " ");
  }
}

// format evidence source - return "video" if source is "transcript", otherwise return the source
export function formatEvidenceSource(
  source: string | undefined | null
): string {
  if (!source) return "";
  return source.toLowerCase() === "transcript" ? "video" : source;
}
