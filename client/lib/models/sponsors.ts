import { Evidence } from "./evidence";

export interface MostRecentAd {
  publication_name: string;
  publication_url: string;
  publication_categories: string[];
  publication_platform: string;
  content_url: string;
  sponsor_type: string;
  published_date: string;
  evidence: Evidence;
}

export interface Sponsor {
  partner_name: string;
  total_ads_found: number;
  most_recent_ad: MostRecentAd;
}
