"use client";

import { useState, useEffect, memo, useRef } from "react";
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

// TODO: just do results combined for sponsors and sponsorships
// reset if search changes

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

  useEffect(() => {
    handleSearch();
  }, []);

  useEffect(() => {
    // Don't clear anything when search type changes
    isInitialLoad.current = false;
  }, [searchType]);

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
        // If no cursor, replace results (new search)
        if (searchType === "category") {
          setSponsorResults(results);
          setSponsorshipResults([]); // Clear sponsorship results when searching categories
        } else {
          setSponsorshipResults(results);
          setSponsorResults([]); // Clear sponsor results when searching brands
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

  // get current results
  const getCurrentResults = () => {
    return searchType === "category" ? sponsorResults : sponsorshipResults;
  };

  const hasResults = () => {
    return getCurrentResults().length > 0;
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
          {/* if no results, then show You've reached the end otherwise, click load more results*/}
          {hasResults() &&
            getCurrentResults().map((result, index) => (
              <div key={index}>
                {searchType === "category" ? (
                  <SponsorResultCard
                    sponsor={result as Sponsor}
                    searchQuery={searchQuery}
                    cursor={cursor}
                  />
                ) : (
                  <SponsorshipResultCard
                    sponsorship={result as Sponsorship}
                    searchQuery={searchQuery}
                    cursor={cursor}
                  />
                )}
              </div>
            ))}
        </div>
        {cursor ? (
          <Button
            onClick={() => handleSearch(searchQuery, cursor)}
            disabled={isLoading}
            className="px-6 self-center text-base"
            variant="ghost"
          >
            {isLoading && <Spinner />}
            {isLoading ? "Loading..." : "Load More"}
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
