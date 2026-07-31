"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { createTodo } from "@/lib/api/todos";

export async function createTodoAction(data: { title: string; body: string }) {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) throw new Error("認証が必要です");

  await createTodo(token, data);
  revalidatePath("/todos");
}
