"use client";

import { useState, useEffect, useRef } from "react";
import SponsorResultCard from "@/components/SponsorResultCard";
import SponsorshipResultCard from "@/components/SponsorshipResultCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { findSponsors, findSponsorships } from "@/lib/services/sponsorships";
import { Sponsor } from "@/lib/models/sponsors";
import { Spinner } from "@/components/ui/spinner";
import { Sponsorship } from "@/lib/models/sponsorship";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("tech");
  const [isSearching, setIsSearching] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [sponsorResults, setSponsorResults] = useState<Sponsor[]>([]);
  const [sponsorshipResults, setSponsorshipResults] = useState<Sponsorship[]>(
    []
  );
  const [searchType, setSearchType] = useState("category");
  const isInitialLoad = useRef(true);

  // initial load
  useEffect(() => {
    handleSearch();
  }, []);

  const handleSearch = async (query?: string, currentCursor?: string) => {
    console.log("currentCursor : ", currentCursor);
    console.log("searchType : ", searchType);

    const searchTerm = query || searchQuery;
    if (!searchTerm.trim()) {
      setError("Please enter an industry or category to search");
      return;
    }

    // if loading more
    if (currentCursor) {
      setIsLoading(true);
    } else {
      setIsSearching(true);
    }

    setError(null);

    try {
      let result;
      if (searchType === "category") {
        result = (await findSponsors(
          searchTerm.trim(),
          undefined,
          currentCursor
        )) as any;
      } else {
        result = (await findSponsorships(
          searchTerm.trim(),
          undefined,
          currentCursor
        )) as any;
      }

      const results = result.results;
      console.log("results : ", results);

      if (currentCursor) {
        // If there's a current cursor, append results to existing ones
        if (searchType === "category") {
          setSponsorResults((prevResults) => [...prevResults, ...results]);
        } else {
          setSponsorshipResults((prevResults) => [...prevResults, ...results]);
        }
      } else {
        // If no cursor, replace results (new search) - only clear the current search type results
        if (searchType === "category") {
          setSponsorResults(results);
        } else {
          setSponsorshipResults(results);
        }
      }

      // set next cursor if available
      setCursor(result.next_cursor);
    } catch (err) {
      setError("Failed to search sponsors. Please try again.");
      console.error("Search error:", err);
    } finally {
      setIsSearching(false);
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  // has results
  const hasResults = () => {
    return sponsorResults.length > 0 || sponsorshipResults.length > 0;
  };

  return (
    <main className="min-h-screen flex flex-col w-full max-w-7xl mx-auto">
      <div
        id="header"
        className="border-b bg-background px-5 md:px-10 sticky top-0 z-10 text-center flex flex-col gap-2 py-5 md:py-10 w-full"
      >
        <div className="flex flex-col gap-4">
          <h1 className="text-start text-2xl md:text-3xl font-semibold text-slate-900 dark:text-white">
            Discover Sponsorships
          </h1>
          <div className="flex flex-col md:flex-row gap-2.5">
            <div className="flex flex-row gap-2.5 w-full">
              <Input
                type="text"
                placeholder={
                  searchType === "category"
                    ? "tech, fitness, gaming"
                    : "Bose or Nike"
                }
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="flex-1"
              />
              <span className="hidden md:block">
                <SearchTypeDropdown
                  value={searchType}
                  onValueChange={setSearchType}
                />
              </span>
              <Button
                onClick={() => handleSearch(searchQuery)}
                disabled={isSearching}
                className="px-6"
              >
                {isSearching ? "Searching..." : "Search"}
              </Button>
            </div>
            <span className="flex md:hidden">
              <SearchTypeDropdown
                value={searchType}
                onValueChange={setSearchType}
                className="w-full"
              />
            </span>
          </div>
        </div>
        {error && (
          <p className="text-red-500 text-sm mt-2 text-center">{error}</p>
        )}
      </div>

      <div
        id="results"
        className="px-5 sm:px-10 py-5 md:py-10 flex flex-col gap-8"
      >
        <div
          id="match-grid"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
        >
          {/* Display all results (both sponsors and sponsorships) */}
          {hasResults() && !isSearching && (
            <>
              {sponsorResults.map((result, index) => (
                <SponsorResultCard
                  key={`sponsor-${index}`}
                  sponsor={result}
                  searchQuery={searchQuery}
                  cursor={cursor}
                />
              ))}
              {sponsorshipResults.map((result, index) => (
                <SponsorshipResultCard
                  key={`sponsorship-${index}`}
                  sponsorship={result}
                  searchQuery={searchQuery}
                  cursor={cursor}
                />
              ))}
            </>
          )}
        </div>
        {cursor || isSearching ? (
          <Button
            onClick={() => handleSearch(searchQuery, cursor || undefined)}
            disabled={isSearching || isLoading}
            className="px-6 self-center text-base"
            variant="ghost"
          >
            {(isSearching || isLoading) && <Spinner />}
            {isSearching || isLoading ? "Loading..." : "Load More"}
          </Button>
        ) : (
          <p className="text-center text-base text-gray-500">
            {hasResults() ? "You've reached the end" : "Nothing yet"}
          </p>
        )}
      </div>
    </main>
  );
}

// search type
interface SearchTypeDropdownProps {
  value: string;
  onValueChange: (value: string) => void;
  className?: string;
}

function SearchTypeDropdown({
  value,
  onValueChange,
  className,
}: SearchTypeDropdownProps) {
  return (
    <Select
      value={value}
      onValueChange={onValueChange}
    >
      <SelectTrigger className={className}>
        <SelectValue placeholder="Select a category" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="category">Video Category</SelectItem>
        <SelectItem value="brand">Brand</SelectItem>
      </SelectContent>
    </Select>
  );
}
