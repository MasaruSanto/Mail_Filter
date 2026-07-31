import { cookies } from "next/headers";
import { redirect, notFound } from "next/navigation";
import Link from "next/link";
import AppHeader from "@/app/_components/AppHeader";
import LogoutButton from "@/app/_components/LogoutButton";
import { getTodo } from "@/lib/api/todos";
import TodoDetailClient from "./TodoDetailClient";

export default async function TodoDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) redirect("/login");

  const todo = await getTodo(token, id).catch(() => null);
  if (!todo) notFound();

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AppHeader actions={<LogoutButton />} />
      <main className="max-w-2xl mx-auto px-6 py-8 space-y-5">
        <Link
          href="/todos"
          className="inline-flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
        >
          ← TODOボードへ戻る
        </Link>
        <TodoDetailClient todo={todo} />
      </main>
    </div>
  );
}
