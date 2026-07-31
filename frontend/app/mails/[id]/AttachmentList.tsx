"use client";

import { useState } from "react";
import type { Attachment } from "@/lib/types/api";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function getBaseUrl() {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function formatSize(size: number | null): string {
  if (size == null) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function IconPaperclip() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
      strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32" />
    </svg>
  );
}

export default function AttachmentList({
  mailId, attachments,
}: { mailId: string; attachments: Attachment[] }) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (attachments.length === 0) return null;

  async function handleDownload(attachment: Attachment) {
    setError(null);
    setDownloadingId(attachment.id);
    try {
      const token = getAuthToken();
      if (!token) throw new Error("ログインが必要です");

      const res = await fetch(
        `${getBaseUrl()}/api/v1/mails/${mailId}/attachments/${attachment.id}/download`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail ?? "ダウンロードに失敗しました");
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = attachment.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ダウンロードに失敗しました");
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
      <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-4">
        添付ファイル（{attachments.length}）
      </h2>
      <ul className="space-y-2">
        {attachments.map((att) => (
          <li key={att.id}>
            <button
              onClick={() => handleDownload(att)}
              disabled={downloadingId === att.id}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50 text-left"
            >
              <IconPaperclip />
              <span className="flex-1 truncate">{att.filename}</span>
              {att.size != null && (
                <span className="text-xs text-zinc-400 shrink-0">{formatSize(att.size)}</span>
              )}
              <span className="text-xs text-zinc-400 shrink-0">
                {downloadingId === att.id ? "取得中..." : "ダウンロード"}
              </span>
            </button>
          </li>
        ))}
      </ul>
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
