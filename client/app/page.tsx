"use client";

import Image from "next/image";
import { useState, useEffect, memo } from "react";
import SponsorshipCard from "@/components/SponsorshipCard";
import SponsorResultCard from "@/components/SponsorResultCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { findSponsors } from "@/lib/services/sponsorships";
import { Sponsor } from "@/lib/models/sponsors";
import videoExamples from "@/lib/video_examples.json";
import { Spinner } from "@/components/ui/spinner";
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
  const [searchResults, setSearchResults] = useState<Sponsor[]>([]);
  const [selectValue, setSelectValue] = useState("category");

  useEffect(() => {
    handleSearch();
  }, []);

  const handleSearch = async (query?: string, currentCursor?: string) => {
    console.log("currentCursor : ", currentCursor);
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
      const result = (await findSponsors(
        searchTerm.trim(),
        undefined,
        currentCursor
      )) as any;
      const sponsors = result.results;

      if (currentCursor) {
        // If there's a current cursor, append results to existing ones
        setSearchResults((prevResults) => [...prevResults, ...sponsors]);
      } else {
        // If no cursor, replace results (new search)
        setSearchResults(sponsors);
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

  return (
    <main className="flex flex-col w-full max-w-7xl mx-auto">
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
                placeholder="Enter industry or category (e.g., tech, fitness, gaming)"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading}
                className="flex-1"
              />
              <span className="hidden md:block">
                <Select
                  value={selectValue}
                  onValueChange={setSelectValue}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="category">Creator Category</SelectItem>
                    <SelectItem value="brand">Brand</SelectItem>
                  </SelectContent>
                </Select>
              </span>
              <Button
                onClick={() => handleSearch(searchQuery)}
                disabled={isLoading}
                className="px-6"
              >
                {isLoading ? "Searching..." : "Search"}
              </Button>
            </div>
            <span className="flex md:hidden">
              <Select
                value={selectValue}
                onValueChange={setSelectValue}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="category">Creator Category</SelectItem>
                  <SelectItem value="brand">Brand</SelectItem>
                </SelectContent>
              </Select>
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
          {searchResults.length > 0
            ? searchResults.map((sponsor, index) => (
                <div key={index}>
                  <SponsorResultCard
                    sponsor={sponsor}
                    searchQuery={searchQuery}
                    cursor={cursor}
                  />
                </div>
              ))
            : videoExamples.video_examples.map((videoUrl, index) => (
                <SponsorshipCard
                  key={index}
                  videoUrl={videoUrl}
                  title={`Video ${index + 1}`}
                >
                  <p>sponsorship description</p>
                </SponsorshipCard>
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
            You've reached the end
          </p>
        )}
      </div>
    </main>
  );
}
