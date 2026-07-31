import { apiFetch } from "./client";
import type { Todo, TodoStatus, TodoPriority } from "../types/api";

const authHeaders = (token: string) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
});

export const getTodos = (token: string): Promise<Todo[]> =>
  apiFetch<Todo[]>("/api/v1/todos", { headers: authHeaders(token) });

export const getTodo = (token: string, id: string): Promise<Todo> =>
  apiFetch<Todo>(`/api/v1/todos/${id}`, { headers: authHeaders(token) });

export const createTodo = (
  token: string,
  data: { title: string; body: string; due_date?: string | null; priority?: TodoPriority }
): Promise<Todo> =>
  apiFetch<Todo>("/api/v1/todos", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });

export const updateTodo = (
  token: string,
  id: string,
  data: { title: string; body: string; due_date?: string | null; priority?: TodoPriority }
): Promise<Todo> =>
  apiFetch<Todo>(`/api/v1/todos/${id}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });

export const updateTodoStatus = (
  token: string,
  id: string,
  status: TodoStatus
): Promise<Todo> =>
  apiFetch<Todo>(`/api/v1/todos/${id}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ status }),
  });

export const deleteTodo = (token: string, id: string): Promise<void> =>
  apiFetch<void>(`/api/v1/todos/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
