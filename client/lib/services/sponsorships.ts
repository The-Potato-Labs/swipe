import { Sponsorship } from "@/lib/models/sponsorship";
import { Sponsor } from "@/lib/models/sponsors";

const UPRIVER_API_KEY = process.env.NEXT_PUBLIC_UPRIVER_API_KEY;
const SPONSOR_API = "https://api.upriver.ai/v1/sponsors";
const SPONSORSHIP_API = "https://api.upriver.ai/v1/sponsorships";

// Generic HTTP request scaffold
async function makeRequest<T>(
  url: string,
  options?: {
    method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
    headers?: Record<string, string>;
    body?: any;
    timeout?: number;
    retries?: number;
  }
): Promise<T> {
  const {
    method = "GET",
    headers = {},
    body,
    timeout = 10000,
    retries = 3,
  } = options || {};

  let lastError: Error;

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const fetchOptions: RequestInit = {
        method,
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        signal: controller.signal,
      };

      // Add body for non-GET requests
      if (body && method !== "GET") {
        fetchOptions.body = JSON.stringify(body);
      }

      const response = await fetch(url, fetchOptions);

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      lastError = error as Error;

      if (attempt < retries) {
        // Exponential backoff
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError!;
}

// Convenience function for GET requests
async function makeGetRequest<T>(
  url: string,
  options?: {
    headers?: Record<string, string>;
    timeout?: number;
    retries?: number;
  }
): Promise<T> {
  return makeRequest<T>(url, { ...options, method: "GET" });
}

// Example usage for sponsors
async function findSponsors(
  categories?: string,
  publication_url?: string,
  cursor?: string
) {
  try {
    const params = new URLSearchParams();

    if (categories) {
      params.append("categories", categories);
    }
    if (publication_url) {
      params.append("publication_url", publication_url);
    }
    if (cursor) {
      params.append("cursor", cursor);
    }

    params.append("platforms", "youtube");
    params.append("top_k_categories", "5");
    params.append("include_evidence", "true");

    const url = `${SPONSOR_API}?${params}`;

    const sponsors = await makeRequest(url, {
      method: "GET",
      headers: {
        "X-Api-Key": UPRIVER_API_KEY!,
      },
      timeout: 999999,
    });
    return sponsors;
  } catch (error) {
    console.error("Failed to fetch sponsors:", error);
    throw error;
  }
}

// Example usage for sponsorships
async function findSponsorships(
  brand?: string,
  publication_url?: string,
  cursor?: string
) {
  // if not brand name or publication url then throw error
  if (!brand && !publication_url) {
    throw new Error("Either brand or publication_url must be provided.");
  }

  try {
    const params = new URLSearchParams();

    if (brand) {
      params.append("brand_name", brand);
    }

    if (publication_url) {
      params.append("publication_url", publication_url);
    }
    if (cursor) {
      params.append("cursor", cursor);
    }

    params.append("platforms", "youtube");
    params.append("top_k_categories", "5");
    params.append("include_evidence", "true");

    const url = `${SPONSORSHIP_API}?${params}`;
    console.log("url : ", url);

    const sponsorships = await makeRequest(url, {
      method: "GET",
      headers: {
        "X-Api-Key": UPRIVER_API_KEY!,
      },
      timeout: 999999,
    });
    return sponsorships;
  } catch (error) {
    console.error("Failed to fetch sponsorships:", error);
    throw error;
  }
}

export { makeRequest, makeGetRequest, findSponsors, findSponsorships };
