"use client";

import Link from "next/link";
import { UserRound, Tag, Calendar, Locate } from "lucide-react";
import { Sponsorship } from "@/lib/models/sponsorship";
import { formatTextToTitleCase, toTitleCase } from "@/lib/utils";

interface SponsorshipMetadataProps {
  sponsorship: Sponsorship;
}

export default function SponsorshipMetadata({
  sponsorship,
}: SponsorshipMetadataProps) {
  const { publication_name, publication_url, sponsor_type, published_date } =
    sponsorship;

  return (
    <div className="flex flex-col gap-2 text-slate-300">
      <p className="flex items-center gap-2">
        <UserRound className="w-4 h-4 text-slate-400" />
        <Link
          href={publication_url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <span className="text-white">{publication_name}</span>
        </Link>
      </p>
      <p className="flex items-center gap-2">
        <Tag className="w-4 h-4 text-slate-400" />
        {formatTextToTitleCase(sponsor_type)}
      </p>
      <p className="flex items-center gap-2">
        <Calendar className="w-4 h-4 text-slate-400" />
        {published_date ? new Date(published_date).toLocaleDateString() : "--"}
      </p>
      {sponsorship.evidence && (
        <p className="flex items-center gap-2">
          <Locate className="w-4 h-4 text-slate-400" />
          <span className="title-case">
            {toTitleCase(sponsorship.evidence.source)}
          </span>
        </p>
      )}
    </div>
  );
}
