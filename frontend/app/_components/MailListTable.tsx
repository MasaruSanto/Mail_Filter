"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { deleteMail } from "@/lib/api/mails";
import type { MailSummary, Priority } from "@/lib/types/api";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const PRIORITY_COLOR: Record<Priority, string> = {
  "迷惑メール": "bg-red-100 text-red-700",
  "業務メール": "bg-blue-100 text-blue-700",
  "営業メール": "bg-yellow-100 text-yellow-700",
  "個人メール": "bg-green-100 text-green-700",
  "緊急メール": "bg-red-100 text-red-800 font-semibold",
  "返信必要": "bg-orange-100 text-orange-700",
  "対応待ち": "bg-zinc-100 text-zinc-600",
  "社内メール": "bg-purple-100 text-purple-700",
};

type Props = {
  mails: MailSummary[];
  total: number;
  offset: number;
  paginationSize: number;
  prevHref: string | null;
  nextHref: string | null;
  hasFilter: boolean;
};

export default function MailListTable({
  mails,
  total,
  offset,
  paginationSize,
  prevHref,
  nextHref,
  hasFilter,
}: Props) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isPending, startTransition] = useTransition();
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const allChecked = mails.length > 0 && mails.every((m) => selected.has(m.id));
  const someChecked = selected.size > 0;

  function toggleAll() {
    if (allChecked) {
      setSelected(new Set());
    } else {
      setSelected(new Set(mails.map((m) => m.id)));
    }
  }

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function handleDeleteSelected() {
    setDeleteError(null);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) { setDeleteError("ログインが必要です"); return; }
      try {
        await Promise.all([...selected].map((id) => deleteMail(token, id)));
        setSelected(new Set());
        router.refresh();
      } catch (err) {
        setDeleteError(err instanceof Error ? err.message : "削除に失敗しました");
      }
    });
  }

  if (mails.length === 0) {
    return (
      <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 py-16 text-center text-sm text-zinc-400">
        {hasFilter ? "条件に一致するメールがありません" : "メールがありません"}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 overflow-hidden">
      {/* 一括削除バー */}
      {someChecked && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-50 dark:bg-zinc-700/50 border-b border-zinc-100 dark:border-zinc-700">
          <span className="text-xs text-zinc-500 dark:text-zinc-400">
            {selected.size} 件選択中
          </span>
          <div className="flex items-center gap-3">
            {deleteError && <span className="text-xs text-red-500">{deleteError}</span>}
            <button
              onClick={() => setSelected(new Set())}
              disabled={isPending}
              className="text-xs text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors disabled:opacity-50"
            >
              選択解除
            </button>
            <button
              onClick={handleDeleteSelected}
              disabled={isPending}
              className="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? "削除中..." : `${selected.size} 件を削除`}
            </button>
          </div>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-100 dark:border-zinc-700">
            <th className="px-4 py-3 w-8">
              <input
                type="checkbox"
                checked={allChecked}
                onChange={toggleAll}
                className="rounded border-zinc-300 dark:border-zinc-500 accent-zinc-700"
              />
            </th>
            <Th>日付</Th>
            <Th>送信者</Th>
            <Th>件名</Th>
            <Th>タグ</Th>
            <Th className="text-center">返信</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-50 dark:divide-zinc-700/50">
          {mails.map((mail) => (
            <tr
              key={mail.id}
              className={`transition-colors ${
                selected.has(mail.id)
                  ? "bg-zinc-50 dark:bg-zinc-700/40"
                  : "hover:bg-zinc-50 dark:hover:bg-zinc-700/30"
              }`}
            >
              <td className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={selected.has(mail.id)}
                  onChange={() => toggleOne(mail.id)}
                  className="rounded border-zinc-300 dark:border-zinc-500 accent-zinc-700"
                />
              </td>
              <td className="px-4 py-3 text-xs text-zinc-400 whitespace-nowrap">
                {mail.day ?? "—"}
              </td>
              <td className="px-4 py-3 text-zinc-700 dark:text-zinc-300 max-w-[140px] truncate">
                {mail.from_name ?? mail.from_email ?? "—"}
              </td>
              <td className="px-4 py-3 text-zinc-800 dark:text-zinc-200 max-w-xs truncate">
                <Link href={`/mails/${mail.id}`} className="hover:underline hover:text-zinc-500 transition-colors">
                  {mail.title ?? "（件名なし）"}
                </Link>
              </td>
              <td className="px-4 py-3">
                {mail.replied_at ? (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400 font-medium">
                    ✓ 返信済み
                  </span>
                ) : mail.priority ? (
                  <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLOR[mail.priority as Priority]}`}>
                    {mail.priority}
                  </span>
                ) : (
                  <span className="text-xs text-zinc-400">未分析</span>
                )}
              </td>
              <td className="px-4 py-3 text-center">
                <span className={mail.needs_immediate_reply ? "text-orange-400" : "text-zinc-200 dark:text-zinc-700"}>
                  ●
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* ページネーション */}
      {total > paginationSize && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-zinc-100 dark:border-zinc-700">
          <span className="text-xs text-zinc-400">
            {offset + 1}〜{Math.min(offset + paginationSize, total)} 件 / 全 {total} 件
          </span>
          <div className="flex gap-2">
            {prevHref && (
              <Link href={prevHref} className="text-xs px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors">
                ← 前へ
              </Link>
            )}
            {nextHref && (
              <Link href={nextHref} className="text-xs px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors">
                次へ →
              </Link>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-4 py-3 text-left text-xs font-medium text-zinc-400 ${className}`}>
      {children}
    </th>
  );
}
