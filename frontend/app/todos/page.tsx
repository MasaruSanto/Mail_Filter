import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTodos } from "@/lib/api/todos";
import AppHeader from "@/app/_components/AppHeader";
import LogoutButton from "@/app/_components/LogoutButton";
import TodoPageClient from "@/app/_components/TodoPageClient";
import type { Todo } from "@/lib/types/api";

export default async function TodoPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;

  if (!token) redirect("/login");

  const todos: Todo[] = await getTodos(token).catch(() => []);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AppHeader actions={<LogoutButton />} />
      <main className="px-6 py-6">
        <TodoPageClient initialTodos={todos} />
      </main>
    </div>
  );
}
