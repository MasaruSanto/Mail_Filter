"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTransition, useRef } from "react";
import type { Priority } from "@/lib/types/api";

const TAGS: Priority[] = [
  "業務メール", "緊急メール", "返信必要", "営業メール",
  "個人メール", "社内メール", "対応待ち", "迷惑メール",
];

export default function MailSearchBar() {
  const router = useRouter();
  const params = useSearchParams();
  const [isPending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);

  const currentQ = params.get("q") ?? "";
  const currentTag = params.get("tag") ?? "";
  const currentNeedsReply = params.get("needs_reply") ?? "";
  const currentDateFrom = params.get("date_from") ?? "";
  const currentDateTo = params.get("date_to") ?? "";

  function pushParams(overrides: Record<string, string>) {
    const next = new URLSearchParams(params.toString());
    Object.entries(overrides).forEach(([k, v]) => {
      if (v) next.set(k, v);
      else next.delete(k);
    });
    startTransition(() => router.push(`/?${next.toString()}`));
  }

  function handleSearch() {
    pushParams({ q: inputRef.current?.value ?? "", offset: "" });
  }

  function handleClear() {
    if (inputRef.current) inputRef.current.value = "";
    startTransition(() => router.push("/"));
  }

  const hasFilter = currentQ || currentTag || currentNeedsReply || currentDateFrom || currentDateTo;

  return (
    <div className="flex flex-wrap gap-2 items-end">
      {/* キーワード */}
      <form onSubmit={(e) => { e.preventDefault(); handleSearch(); }} className="flex gap-1.5">
        <input
          ref={inputRef}
          type="text"
          defaultValue={currentQ}
          placeholder="キーワード検索…"
          className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 w-52"
        />
        <button
          type="submit"
          disabled={isPending}
          className="px-3 py-1.5 text-sm rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50"
        >
          検索
        </button>
      </form>

      {/* タグ */}
      <select
        value={currentTag}
        onChange={(e) => pushParams({ tag: e.target.value, offset: "" })}
        className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-400"
      >
        <option value="">すべてのタグ</option>
        {TAGS.map((t) => <option key={t} value={t}>{t}</option>)}
      </select>

      {/* 即返信 */}
      <select
        value={currentNeedsReply}
        onChange={(e) => pushParams({ needs_reply: e.target.value, offset: "" })}
        className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-400"
      >
        <option value="">返信：すべて</option>
        <option value="true">返信必要</option>
        <option value="false">返信不要</option>
      </select>

      {/* 日付範囲 */}
      <div className="flex items-center gap-1">
        <input
          type="date"
          value={currentDateFrom}
          onChange={(e) => pushParams({ date_from: e.target.value, offset: "" })}
          className="px-2 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-400"
        />
        <span className="text-xs text-zinc-400">〜</span>
        <input
          type="date"
          value={currentDateTo}
          onChange={(e) => pushParams({ date_to: e.target.value, offset: "" })}
          className="px-2 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-zinc-400"
        />
      </div>

      {/* クリア */}
      {hasFilter && (
        <button
          onClick={handleClear}
          disabled={isPending}
          className="px-3 py-1.5 text-sm rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
        >
          クリア
        </button>
      )}

      {isPending && (
        <span className="text-xs text-zinc-400 self-center">読み込み中…</span>
      )}
    </div>
  );
}
