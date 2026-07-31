export default function Loading() {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 animate-pulse">
      <header className="bg-white dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700 px-6 py-4 flex items-center justify-between">
        <div className="h-6 w-36 bg-zinc-200 dark:bg-zinc-700 rounded" />
        <div className="h-9 w-36 bg-zinc-200 dark:bg-zinc-700 rounded-lg" />
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* 統計カードスケルトン */}
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 px-5 py-4"
            >
              <div className="h-3 w-16 bg-zinc-200 dark:bg-zinc-700 rounded mb-3" />
              <div className="h-8 w-10 bg-zinc-200 dark:bg-zinc-700 rounded" />
            </div>
          ))}
        </div>

        {/* テーブルスケルトン */}
        <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="flex gap-4 px-4 py-3 border-b border-zinc-50 dark:border-zinc-700/50 last:border-0"
            >
              <div className="h-4 w-20 bg-zinc-100 dark:bg-zinc-700 rounded" />
              <div className="h-4 w-28 bg-zinc-100 dark:bg-zinc-700 rounded" />
              <div className="h-4 flex-1 bg-zinc-100 dark:bg-zinc-700 rounded" />
              <div className="h-4 w-16 bg-zinc-100 dark:bg-zinc-700 rounded" />
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
