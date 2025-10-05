import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Spinner } from "@/components/ui/spinner";
import { useState } from "react";

interface SponsorshipSheetProps {
  videoUrl: string;
  title: string;
  children: React.ReactNode;
  sheetChildren: React.ReactNode;
}

const enrichedDetails = [
  {
    label: "Detail 1",
    content:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
  },
  {
    label: "Detail 2",
    content:
      "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
  },
];

const SponsorshipSheet: React.FC<SponsorshipSheetProps> = ({
  videoUrl,
  title,
  children,
  sheetChildren,
}) => {
  const [isLoading, setIsLoading] = useState(true);

  // TODO: based on video url, extract more information

  return (
    <Sheet>
      <SheetTrigger>{children}</SheetTrigger>
      <SheetContent className="gap-2">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription className="mt-4 px-0">
            <span className="aspect-video w-full">
              <iframe
                src={videoUrl}
                title={title}
                className="w-full h-full rounded-md"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </span>
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4 text-sm">
          {/* same as content from card */}
          {sheetChildren}
          {/* enriched details */}
          {/* is analyzing video */}
          {isLoading ? (
            <div className="flex flex-row items-center gap-2">
              <Spinner className="w-4 h-4 text-slate-400" />{" "}
              <p>Analyzing video...</p>
            </div>
          ) : (
            enrichedDetails.map((detail, index) => (
              <div
                key={`detail-${index}`}
                className="flex flex-col gap-0.5"
              >
                <h3>{detail.label}</h3>
                <p className="text-sm text-slate-400">{detail.content}</p>
              </div>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default SponsorshipSheet;
