import { NextRequest, NextResponse } from "next/server";

const UPRIVER_API_KEY = process.env.NEXT_PUBLIC_UPRIVER_API_KEY;
const SPONSORSHIP_API = "https://api.upriver.ai/v1/sponsorships";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const brand_name = searchParams.get("brand_name");
  const publication_url = searchParams.get("publication_url");
  const cursor = searchParams.get("cursor");

  if (!brand_name && !publication_url) {
    return NextResponse.json(
      { error: "Either brand_name or publication_url parameter is required" },
      { status: 400 }
    );
  }

  if (!UPRIVER_API_KEY) {
    return NextResponse.json(
      { error: "API key not configured" },
      { status: 500 }
    );
  }

  try {
    const params = new URLSearchParams();

    if (brand_name) {
      params.append("brand_name", brand_name);
    }
    if (publication_url) {
      params.append("publication_url", publication_url);
    }
    if (cursor) {
      params.append("cursor", cursor);
    }

    // Configure required parameters
    params.append("platforms", "youtube");
    params.append("top_k_categories", "5");
    params.append("include_evidence", "true");

    const url = `${SPONSORSHIP_API}?${params}`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "X-Api-Key": UPRIVER_API_KEY,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to fetch sponsorships:", error);
    return NextResponse.json(
      { error: "Failed to fetch sponsorships" },
      { status: 500 }
    );
  }
}
