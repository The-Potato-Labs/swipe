import { NextRequest, NextResponse } from "next/server";

const UPRIVER_API_KEY = process.env.UPRIVER_API_KEY;
const SPONSOR_API = "https://api.upriver.ai/v1/sponsors";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const categories = searchParams.get("categories");
  const publication_url = searchParams.get("publication_url");

  if (!categories && !publication_url) {
    return NextResponse.json(
      { error: "Either categories or publication_url parameter is required" },
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

    if (categories) {
      params.append("categories", categories);
    }
    if (publication_url) {
      params.append("publication_url", publication_url);
    }

    // Configure required parameters
    params.append("platforms", "youtube");
    params.append("top_k_categories", "5");

    const url = `${SPONSOR_API}?${params}`;

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
    console.error("Failed to fetch sponsors:", error);
    return NextResponse.json(
      { error: "Failed to fetch sponsors" },
      { status: 500 }
    );
  }
}
