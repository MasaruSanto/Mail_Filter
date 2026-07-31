import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import AppHeader from "@/app/_components/AppHeader";
import GoogleAuthBanner from "@/app/_components/GoogleAuthBanner";
import LogoutButton from "@/app/_components/LogoutButton";
import CalendarView from "@/app/_components/CalendarView";
import type { CalendarEvent } from "@/lib/types/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export default async function CalendarPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) redirect("/login");

  let events: CalendarEvent[] = [];
  let googleAuthorized = true;

  try {
    const res = await fetch(`${BASE_URL}/api/v1/calendar/events`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (res.status === 403) {
      googleAuthorized = false;
    } else if (res.ok) {
      events = await res.json();
    }
  } catch {}

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <GoogleAuthBanner />
      <AppHeader actions={<LogoutButton />} />

      <main className="max-w-2xl mx-auto px-6 py-8 space-y-4">
        {!googleAuthorized && (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-zinc-300 dark:border-zinc-600 px-4 py-3 text-xs text-zinc-400">
            <span>Googleカレンダー未連携 — 連携後にイベントが表示されます</span>
          </div>
        )}
        <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
          <CalendarView initialEvents={events} token={token} />
        </div>
      </main>
    </div>
  );
}
