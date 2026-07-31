"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { runPipeline } from "@/lib/api/pipeline";
import { PIPELINE_MAX_RESULTS_KEY, PIPELINE_AFTER_DAYS_KEY } from "@/app/settings/SettingsClient";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function getMaxResults(): number {
  const saved = localStorage.getItem(PIPELINE_MAX_RESULTS_KEY);
  return saved ? Number(saved) : 10;
}

function getAfterDays(): number | null {
  const saved = localStorage.getItem(PIPELINE_AFTER_DAYS_KEY);
  if (saved === null) return 30;
  return saved === "null" ? null : Number(saved);
}

export default function PipelineButton() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState<string | null>(null);

  const handleRun = () => {
    startTransition(async () => {
      setMessage(null);
      const token = getAuthToken();
      if (!token) {
        setMessage("ログインが必要です");
        return;
      }
      try {
        const result = await runPipeline(token, getMaxResults(), getAfterDays());
        if (result.errors.length > 0) {
          setMessage(`${result.processed}件を処理しました（一部エラーあり）`);
        } else {
          setMessage(`${result.processed}件を処理しました`);
        }
        router.refresh();
      } catch (e) {
        setMessage(e instanceof Error ? e.message : "エラーが発生しました");
      }
    });
  };

  return (
    <div className="flex items-center gap-3">
      {message && (
        <span className="text-sm text-zinc-500 dark:text-zinc-400">
          {message}
        </span>
      )}
      <button
        onClick={handleRun}
        disabled={isPending}
        className="text-sm px-4 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-white dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {isPending ? "処理中..." : "メールを取得・分析"}
      </button>
    </div>
  );
}
