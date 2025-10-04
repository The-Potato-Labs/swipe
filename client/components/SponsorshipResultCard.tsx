"use client";

import { memo } from "react";
import SponsorshipCard from "@/components/SponsorshipCard";
import SponsorshipMetadata from "@/components/SponsorshipMetadata";
import { Sponsorship } from "@/lib/models/sponsorship";

interface SponsorshipResultCardProps {
  sponsorship: Sponsorship;
  searchQuery: string;
  cursor: string | null;
}

const SponsorshipResultCard = memo(function SponsorshipResultCard({
  sponsorship,
}: SponsorshipResultCardProps) {
  return (
    <SponsorshipCard
      videoUrl={sponsorship.content_url}
      title={sponsorship.content_title}
    >
      <SponsorshipMetadata sponsorship={sponsorship} />
    </SponsorshipCard>
  );
});

export default SponsorshipResultCard;
