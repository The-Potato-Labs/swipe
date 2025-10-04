import Image from "next/image";

export default function Footer() {
  return (
    <footer className="text-sm px-5 md:px-10 py-10 flex gap-[24px] flex-wrap items-center justify-center xl:justify-end">
      <a
        className="flex items-center gap-2 hover:underline hover:underline-offset-4"
        href="https://upriver.ai"
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
        Go to upriver.ai →
      </a>
    </footer>
  );
}
