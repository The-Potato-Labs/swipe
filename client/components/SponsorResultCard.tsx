"use client";

import { memo } from "react";
import SponsorshipCard from "@/components/SponsorshipCard";
import SponsorMetadata from "@/components/SponsorMetadata";
import { Sponsor } from "@/lib/models/sponsors";

interface SponsorResultCardProps {
  sponsor: Sponsor;
  searchQuery: string;
  cursor: string | null;
}

const SponsorResultCard = memo(function SponsorResultCard({
  sponsor,
}: SponsorResultCardProps) {
  console.log("sponsor : ", sponsor);
  return (
    <SponsorshipCard
      videoUrl={sponsor.most_recent_ad.content_url}
      offset_seconds={sponsor.most_recent_ad?.evidence?.offset_seconds}
      title={sponsor.partner_name}
    >
      <SponsorMetadata sponsor={sponsor} />
    </SponsorshipCard>
  );
});

export default SponsorResultCard;
