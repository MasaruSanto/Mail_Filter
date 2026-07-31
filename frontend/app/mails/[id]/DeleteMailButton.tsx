"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { deleteMail } from "@/lib/api/mails";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function DeleteMailButton({ mailId }: { mailId: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [confirming, setConfirming] = useState(false);

  function handleClick() {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setError(null);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) {
        setError("ログインが必要です");
        return;
      }
      try {
        await deleteMail(token, mailId);
        router.push("/");
      } catch (err) {
        setConfirming(false);
        setError(err instanceof Error ? err.message : "削除に失敗しました");
      }
    });
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {confirming && !isPending && (
          <button
            onClick={() => setConfirming(false)}
            className="text-sm px-3 py-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
          >
            キャンセル
          </button>
        )}
        <button
          onClick={handleClick}
          disabled={isPending}
          className={`text-sm px-4 py-1.5 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            confirming
              ? "bg-red-600 text-white hover:bg-red-700"
              : "border border-red-300 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
          }`}
        >
          {isPending ? "削除中..." : confirming ? "本当に削除する" : "削除"}
        </button>
      </div>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
