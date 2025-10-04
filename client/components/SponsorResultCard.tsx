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
  return (
    <SponsorshipCard
      videoUrl={sponsor.most_recent_ad.content_url}
      title={sponsor.partner_name}
    >
      <SponsorMetadata sponsor={sponsor} />
    </SponsorshipCard>
  );
});

export default SponsorResultCard;
