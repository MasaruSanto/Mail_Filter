"use client";

import { useState, useRef, useTransition } from "react";
import Link from "next/link";
import type { Todo, TodoStatus, TodoPriority } from "@/lib/types/api";

const ALL_STATUSES: TodoStatus[] = ["未対応", "処理中", "処理済み", "完了"];
const ALL_PRIORITIES: TodoPriority[] = ["高", "中", "低"];

const PRIORITY_STYLE: Record<TodoPriority, string> = {
  高: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400",
  中: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400",
  低: "bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400",
};

const STATUS_STYLE: Record<
  TodoStatus,
  { dot: string; countBg: string; border: string; dropBorder: string; dropBg: string }
> = {
  未対応: {
    dot: "bg-zinc-400",
    countBg: "bg-zinc-100 text-zinc-600 dark:bg-zinc-700 dark:text-zinc-300",
    border: "border-zinc-200 dark:border-zinc-700",
    dropBorder: "border-zinc-400",
    dropBg: "bg-zinc-50 dark:bg-zinc-700/40",
  },
  処理中: {
    dot: "bg-blue-500",
    countBg: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
    border: "border-blue-100 dark:border-blue-900/40",
    dropBorder: "border-blue-400",
    dropBg: "bg-blue-50 dark:bg-blue-900/30",
  },
  処理済み: {
    dot: "bg-orange-400",
    countBg: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
    border: "border-orange-100 dark:border-orange-900/40",
    dropBorder: "border-orange-400",
    dropBg: "bg-orange-50 dark:bg-orange-900/20",
  },
  完了: {
    dot: "bg-green-500",
    countBg: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300",
    border: "border-green-100 dark:border-green-900/40",
    dropBorder: "border-green-400",
    dropBg: "bg-green-50 dark:bg-green-900/20",
  },
};

type EditTarget = { id: string; title: string; body: string; dueDate: string; priority: TodoPriority };

type Props = {
  todos: Todo[];
  onStatusChangeAction: (id: string, status: TodoStatus) => void;
  onEditAction: (id: string, data: { title: string; body: string; due_date: string | null; priority: TodoPriority }) => Promise<void>;
  onDeleteAction: (id: string) => void;
};

export default function TodoBoard({ todos, onStatusChangeAction, onEditAction, onDeleteAction }: Props) {
  const [dragOver, setDragOver] = useState<TodoStatus | null>(null);
  const [editing, setEditing] = useState<EditTarget | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const dragId = useRef<string | null>(null);

  function handleDragStart(e: React.DragEvent, id: string) {
    dragId.current = id;
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDragOver(e: React.DragEvent, status: TodoStatus) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setDragOver(status);
  }

  function handleDragLeave(e: React.DragEvent) {
    if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) {
      setDragOver(null);
    }
  }

  function handleDrop(e: React.DragEvent, status: TodoStatus) {
    e.preventDefault();
    setDragOver(null);
    const id = dragId.current;
    dragId.current = null;
    if (!id) return;
    const dragged = todos.find((t) => t.id === id);
    if (!dragged || dragged.status === status) return;
    onStatusChangeAction(id, status);
  }

  function openEdit(todo: Todo) {
    setEditing({
      id: todo.id,
      title: todo.title ?? "",
      body: todo.body ?? "",
      dueDate: todo.due_date ? todo.due_date.slice(0, 10) : "",
      priority: todo.priority ?? "中",
    });
    setEditError(null);
  }

  function handleEditSubmit(e: { preventDefault(): void }) {
    e.preventDefault();
    if (!editing || !editing.title.trim()) return;
    startTransition(async () => {
      try {
        await onEditAction(editing.id, {
          title: editing.title.trim(),
          body: editing.body.trim(),
          due_date: editing.dueDate ? new Date(editing.dueDate).toISOString() : null,
          priority: editing.priority,
        });
        setEditing(null);
      } catch {
        setEditError("保存に失敗しました");
      }
    });
  }

  const byStatus = Object.fromEntries(
    ALL_STATUSES.map((s) => [s, todos.filter((t) => t.status === s)])
  ) as Record<TodoStatus, Todo[]>;

  return (
    <>
      <div className="flex gap-4 items-start overflow-x-auto pb-6">
        {ALL_STATUSES.map((status) => {
          const style = STATUS_STYLE[status];
          const items = byStatus[status];
          const isOver = dragOver === status;
          return (
            <div
              key={status}
              className="flex-shrink-0 w-72"
              onDragOver={(e) => handleDragOver(e, status)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, status)}
            >
              <div className="flex items-center gap-2 mb-3 px-1">
                <span className={`w-2 h-2 rounded-full shrink-0 ${style.dot}`} />
                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  {status}
                </span>
                <span className={`ml-auto text-xs font-medium px-1.5 py-0.5 rounded-full ${style.countBg}`}>
                  {items.length}
                </span>
              </div>

              <div
                className={`min-h-52 rounded-xl border p-2 space-y-2 transition-colors ${
                  isOver
                    ? `${style.dropBorder} ${style.dropBg}`
                    : `${style.border} bg-white dark:bg-zinc-800`
                }`}
              >
                {items.length === 0 ? (
                  <p className="text-center text-xs text-zinc-300 dark:text-zinc-600 py-10">
                    なし
                  </p>
                ) : (
                  items.map((todo) => (
                    <TodoCard
                      key={todo.id}
                      todo={todo}
                      onDragStart={(e) => handleDragStart(e, todo.id)}
                      onEdit={() => openEdit(todo)}
                      onDelete={() => onDeleteAction(todo.id)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 編集モーダル */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
              TODOを編集
            </h3>
            <form onSubmit={handleEditSubmit} className="space-y-3">
              <div>
                <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                  タイトル <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={editing.title}
                  onChange={(e) => setEditing({ ...editing, title: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                  詳細
                </label>
                <textarea
                  value={editing.body}
                  onChange={(e) => setEditing({ ...editing, body: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400 resize-none"
                />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                    終了日
                  </label>
                  <input
                    type="date"
                    value={editing.dueDate}
                    onChange={(e) => setEditing({ ...editing, dueDate: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  />
                </div>
                <div className="w-28">
                  <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">
                    優先度
                  </label>
                  <select
                    value={editing.priority}
                    onChange={(e) => setEditing({ ...editing, priority: e.target.value as TodoPriority })}
                    className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400"
                  >
                    {ALL_PRIORITIES.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>
              {editError && <p className="text-xs text-red-500">{editError}</p>}
              <div className="flex gap-2 justify-end pt-1">
                <button
                  type="button"
                  onClick={() => setEditing(null)}
                  disabled={isPending}
                  className="text-sm px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={isPending || !editing.title.trim()}
                  className="text-sm px-4 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isPending ? "保存中..." : "保存"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}

function TodoCard({
  todo,
  onDragStart,
  onEdit,
  onDelete,
}: {
  todo: Todo;
  onDragStart: (e: React.DragEvent) => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (window.confirm("このTODOを削除しますか？")) onDelete();
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-700 rounded-lg p-3 shadow-sm hover:shadow-md transition-all cursor-grab active:cursor-grabbing active:opacity-50 active:scale-95 group"
    >
      <div className="flex items-start justify-between gap-1 mb-1">
        <Link
          href={`/todos/${todo.id}`}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          className="text-sm font-medium text-zinc-900 dark:text-zinc-100 leading-snug line-clamp-2 flex-1 hover:underline hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        >
          {todo.title ?? "（タイトルなし）"}
        </Link>
        {todo.priority && (
          <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded-full font-medium ${PRIORITY_STYLE[todo.priority]}`}>
            {todo.priority}
          </span>
        )}
        <div className="shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all">
          {todo.status === "完了" && (
            <button
              onClick={handleDelete}
              onMouseDown={(e) => e.stopPropagation()}
              className="text-xs px-1.5 py-0.5 rounded text-zinc-400 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-900/20 transition-all"
            >
              削除
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onEdit(); }}
            onMouseDown={(e) => e.stopPropagation()}
            className="text-xs px-1.5 py-0.5 rounded text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 dark:hover:text-zinc-200 dark:hover:bg-zinc-700 transition-all"
          >
            編集
          </button>
        </div>
      </div>
      {todo.body && (
        <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 mb-2 leading-relaxed">
          {todo.body}
        </p>
      )}
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
        <p className="text-xs text-zinc-300 dark:text-zinc-600">
          追加: {todo.created_at.slice(0, 10)}
        </p>
        {todo.due_date && (
          <p className={`text-xs font-medium ${
            new Date(todo.due_date) < new Date()
              ? "text-red-400 dark:text-red-400"
              : "text-blue-400 dark:text-blue-400"
          }`}>
            期限: {todo.due_date.slice(0, 10)}
          </p>
        )}
      </div>
    </div>
  );
}
