import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetTrigger,
} from "@/components/ui/sheet";

interface SponsorshipSheetProps {
  videoUrl: string;
  title: string;
  description: string;
  children: React.ReactNode;
}

const SponsorshipSheet: React.FC<SponsorshipSheetProps> = ({
  videoUrl,
  title,
  description,
  children,
}) => {
  return (
    <Sheet>
      <SheetTrigger>{children}</SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <SheetDescription>{description}</SheetDescription>
      </SheetContent>
    </Sheet>
  );
};

export default SponsorshipSheet;
