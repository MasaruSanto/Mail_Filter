"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import type { Todo, TodoStatus, TodoPriority } from "@/lib/types/api";
import { updateTodo, updateTodoStatus } from "@/lib/api/todos";

const ALL_STATUSES: TodoStatus[] = ["未対応", "処理中", "処理済み", "完了"];
const ALL_PRIORITIES: TodoPriority[] = ["高", "中", "低"];

const STATUS_STYLE: Record<TodoStatus, string> = {
  未対応: "bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300",
  処理中: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  処理済み: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  完了: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
};

const PRIORITY_STYLE: Record<TodoPriority, string> = {
  高: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
  中: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
  低: "bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400",
};

function getAuthToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]+)/);
  return match ? match[1] : null;
}

type EditState = {
  title: string;
  body: string;
  dueDate: string;
  priority: TodoPriority;
};

export default function TodoDetailClient({ todo }: { todo: Todo }) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<EditState>({
    title: todo.title ?? "",
    body: todo.body ?? "",
    dueDate: todo.due_date ? todo.due_date.slice(0, 10) : "",
    priority: todo.priority ?? "中",
  });
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const inputClass =
    "w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

  function handleStatusChange(status: TodoStatus) {
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) return;
      try {
        await updateTodoStatus(token, todo.id, status);
        router.refresh();
      } catch {
        setError("ステータスの更新に失敗しました");
      }
    });
  }

  function handleEditSubmit() {
    if (!form.title.trim()) return;
    setError(null);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) return;
      try {
        await updateTodo(token, todo.id, {
          title: form.title.trim(),
          body: form.body.trim(),
          due_date: form.dueDate ? new Date(form.dueDate).toISOString() : null,
          priority: form.priority,
        });
        setEditing(false);
        router.refresh();
      } catch {
        setError("保存に失敗しました");
      }
    });
  }

  const currentStatus = todo.status ?? "未対応";
  const isOverdue = todo.due_date && new Date(todo.due_date) < new Date() && currentStatus !== "完了";

  return (
    <div className="space-y-5">
      {/* ステータス + タイトル */}
      <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6 space-y-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* ステータス切替 */}
          <div className="flex flex-wrap gap-2">
            {ALL_STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => handleStatusChange(s)}
                disabled={isPending || s === currentStatus}
                className={`text-xs px-3 py-1 rounded-full font-medium transition-all border ${
                  s === currentStatus
                    ? `${STATUS_STYLE[s]} border-transparent cursor-default`
                    : "border-zinc-200 dark:border-zinc-600 text-zinc-400 hover:border-zinc-400 dark:hover:border-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                } disabled:opacity-60`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* 編集ボタン */}
          {!editing && (
            <button
              onClick={() => { setEditing(true); setError(null); }}
              className="text-sm px-4 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
            >
              編集
            </button>
          )}
        </div>

        {editing ? (
          <form onSubmit={(e) => { e.preventDefault(); handleEditSubmit(); }} className="space-y-3">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">タイトル <span className="text-red-400">*</span></label>
              <input
                type="text"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">詳細</label>
              <textarea
                rows={6}
                value={form.body}
                onChange={(e) => setForm({ ...form, body: e.target.value })}
                className={`${inputClass} resize-y`}
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs text-zinc-400 mb-1">期限</label>
                <input
                  type="date"
                  value={form.dueDate}
                  onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div className="w-28">
                <label className="block text-xs text-zinc-400 mb-1">優先度</label>
                <select
                  value={form.priority}
                  onChange={(e) => setForm({ ...form, priority: e.target.value as TodoPriority })}
                  className={inputClass}
                >
                  {ALL_PRIORITIES.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => { setEditing(false); setError(null); }}
                disabled={isPending}
                className="text-sm px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                キャンセル
              </button>
              <button
                type="submit"
                disabled={isPending || !form.title.trim()}
                className="text-sm px-5 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPending ? "保存中..." : "保存"}
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 leading-snug">
                {todo.title ?? "（タイトルなし）"}
              </h1>
              {todo.priority && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PRIORITY_STYLE[todo.priority]}`}>
                  優先度: {todo.priority}
                </span>
              )}
            </div>

            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-zinc-400 whitespace-nowrap">期限</dt>
              <dd suppressHydrationWarning className={`font-medium ${isOverdue ? "text-red-500" : "text-zinc-700 dark:text-zinc-300"}`}>
                {todo.due_date ? todo.due_date.slice(0, 10) : "—"}
                {isOverdue && <span className="ml-2 text-xs text-red-400">期限超過</span>}
              </dd>

              <dt className="text-zinc-400 whitespace-nowrap">作成日</dt>
              <dd suppressHydrationWarning className="text-zinc-500 dark:text-zinc-400">
                {todo.created_at.slice(0, 10)}
              </dd>
            </dl>
          </>
        )}
      </div>

      {/* 本文 */}
      {!editing && (
        <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
          <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-4">詳細</h2>
          {todo.body ? (
            <pre className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap break-words font-sans leading-relaxed">
              {todo.body}
            </pre>
          ) : (
            <p className="text-sm text-zinc-400">詳細はありません</p>
          )}
        </div>
      )}

      {error && !editing && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
