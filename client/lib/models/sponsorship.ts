export interface Evidence {
  source: string;
  excerpt: string;
  offset_seconds: number;
  confidence: number;
}

export interface Sponsorship {
  partner_name: string;
  sponsor_type: string;
  partner_confidence: number;
  publication_name: string;
  publication_url: string;
  publication_categories: string[];
  publication_platform: string;
  content_title: string;
  content_url: string;
  published_date: string;
  evidence: Evidence;
}
