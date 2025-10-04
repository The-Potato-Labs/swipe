import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Sponsor } from "@/lib/models/sponsors";
import SponsorshipMetadata from "@/components/SponsorshipMetadata";

interface SponsorshipSheetProps {
  videoUrl: string;
  title: string;
  children: React.ReactNode;
  sheetChildren: React.ReactNode;
}

const SponsorshipSheet: React.FC<SponsorshipSheetProps> = ({
  videoUrl,
  title,
  children,
  sheetChildren,
}) => {
  return (
    <Sheet>
      <SheetTrigger>{children}</SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription className="mt-4">
            <span className="aspect-video w-full">
              <iframe
                src={videoUrl}
                title={title}
                className="w-full h-full rounded-lg"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </span>
          </SheetDescription>
        </SheetHeader>
        <div className="flex flex-col gap-4 px-4">{sheetChildren}</div>
      </SheetContent>
    </Sheet>
  );
};

export default SponsorshipSheet;
