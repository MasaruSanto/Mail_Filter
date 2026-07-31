import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getMe } from "@/lib/api/auth";
import AppHeader from "@/app/_components/AppHeader";
import LogoutButton from "@/app/_components/LogoutButton";
import SettingsClient from "./SettingsClient";

export default async function SettingsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) redirect("/login");

  const user = await getMe(token).catch(() => null);
  if (!user) redirect("/login");

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AppHeader actions={<LogoutButton />} />
      <main className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-6">
          設定
        </h1>
        <SettingsClient user={user} token={token} />
      </main>
    </div>
  );
}
