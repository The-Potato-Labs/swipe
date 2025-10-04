import Image from "next/image";
import SponsorshipCard from "@/components/SponsorshipCard";
import videoExamples from "@/lib/video_examples.json";

export default function Home() {
  return (
    <div className="font-sans flex flex-col min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-14 w-full max-w-7xl mx-auto">
        <div
          id="header"
          className="text-center"
        >
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Sponsorship Search
          </h1>
        </div>

        <div
          id="match-grid"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6"
        >
          {videoExamples.video_examples.map((videoUrl, index) => (
            <SponsorshipCard
              key={index}
              videoUrl={videoUrl}
              title={`Video ${index + 1}`}
              description={`This is a sample description for video ${
                index + 1
              }. Click to watch and discover more content.`}
            />
          ))}
        </div>
      </main>
      <footer className="flex gap-[24px] flex-wrap items-center justify-center">
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/file.svg"
            alt="File icon"
            width={16}
            height={16}
          />
          Learn
        </a>
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/window.svg"
            alt="Window icon"
            width={16}
            height={16}
          />
          Examples
        </a>
        <a
          className="flex items-center gap-2 hover:underline hover:underline-offset-4"
          href="https://nextjs.org?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Image
            aria-hidden
            src="/globe.svg"
            alt="Globe icon"
            width={16}
            height={16}
          />
          Go to nextjs.org →
        </a>
      </footer>
    </div>
  );
}
