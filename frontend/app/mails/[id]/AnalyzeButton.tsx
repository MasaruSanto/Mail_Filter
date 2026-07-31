"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { analyzeMail } from "@/lib/api/mails";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function AnalyzeButton({ mailId }: { mailId: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleAnalyze() {
    setError(null);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) {
        setError("ログインが必要です");
        return;
      }
      try {
        await analyzeMail(token, mailId);
        router.refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "分析に失敗しました");
      }
    });
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleAnalyze}
        disabled={isPending}
        className="text-sm px-4 py-1.5 bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 rounded-lg hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isPending ? "分析中..." : "AI分析する"}
      </button>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
