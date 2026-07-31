"use client";

import { useState } from "react";
import type { Todo, TodoStatus, TodoPriority } from "@/lib/types/api";
import { updateTodoStatus, updateTodo, deleteTodo } from "@/lib/api/todos";
import TodoBoard from "./TodoBoard";
import AddTodoButton from "./AddTodoButton";

function getAuthToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]+)/);
  return match ? match[1] : null;
}

export default function TodoPageClient({ initialTodos }: { initialTodos: Todo[] }) {
  const [todos, setTodos] = useState<Todo[]>(initialTodos);

  function handleCreated(todo: Todo) {
    setTodos((prev) => [todo, ...prev]);
  }

  async function handleStatusChange(id: string, status: TodoStatus) {
    const prev = todos;
    setTodos((ts) => ts.map((t) => (t.id === id ? { ...t, status } : t)));
    const token = getAuthToken();
    if (!token) { setTodos(prev); return; }
    try {
      await updateTodoStatus(token, id, status);
    } catch {
      setTodos(prev);
    }
  }

  async function handleEdit(id: string, data: { title: string; body: string; due_date: string | null; priority: TodoPriority }) {
    const prev = todos;
    setTodos((ts) => ts.map((t) => (t.id === id ? { ...t, ...data } : t)));
    const token = getAuthToken();
    if (!token) { setTodos(prev); return; }
    try {
      await updateTodo(token, id, data);
    } catch {
      setTodos(prev);
    }
  }

  async function handleDelete(id: string) {
    const prev = todos;
    setTodos((ts) => ts.filter((t) => t.id !== id));
    const token = getAuthToken();
    if (!token) { setTodos(prev); return; }
    try {
      await deleteTodo(token, id);
    } catch {
      setTodos(prev);
    }
  }

  return (
    <>
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-base font-semibold text-zinc-800 dark:text-zinc-100">
            TODOボード
          </h2>
          <span className="text-xs text-zinc-400">{todos.length} 件</span>
        </div>
        <AddTodoButton onCreatedAction={handleCreated} />
      </div>
      <TodoBoard
        todos={todos}
        onStatusChangeAction={handleStatusChange}
        onEditAction={handleEdit}
        onDeleteAction={handleDelete}
      />
    </>
  );
}
