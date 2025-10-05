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
  console.log("offset seconds : ", sponsorship.evidence?.offset_seconds);
  return (
    <SponsorshipCard
      videoUrl={sponsorship.content_url}
      offset_seconds={sponsorship.evidence?.offset_seconds}
      title={sponsorship.partner_name}
      showCardTitle={false}
    >
      <SponsorshipMetadata sponsorship={sponsorship} />
    </SponsorshipCard>
  );
});

export default SponsorshipResultCard;
