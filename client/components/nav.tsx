export default function Nav() {
  return (
    <nav className="sticky top-0 w-full bg-background border-b px-5 md:px-10 py-5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
          Swipe
        </h2>
        <div className="text-base flex items-center gap-6">
          <button className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white font-medium">
            Discover
          </button>
          <button className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white font-medium">
            Favorites
          </button>
        </div>
      </div>
    </nav>
  );
}
