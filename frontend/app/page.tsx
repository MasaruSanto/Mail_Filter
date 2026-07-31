import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import { getMails } from "@/lib/api/mails";
import { getStats } from "@/lib/api/stats";
import AppHeader from "./_components/AppHeader";
import GoogleAuthBanner from "./_components/GoogleAuthBanner";
import LogoutButton from "./_components/LogoutButton";
import PipelineButton from "./_components/PipelineButton";
import MailSearchBar from "./_components/MailSearchBar";
import MailListTable from "./_components/MailListTable";

const PAGINATION_SIZE = 30;

type SearchParams = {
  q?: string;
  tag?: string;
  needs_reply?: string;
  date_from?: string;
  date_to?: string;
  offset?: string;
};

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) redirect("/login");

  const sp = await searchParams;
  const offset = Number(sp.offset ?? 0);

  const [stats, mailsRes] = await Promise.all([
    getStats(token).catch(() => null),
    getMails(token, {
      q: sp.q,
      tag: sp.tag,
      needs_reply: sp.needs_reply === "true" ? true : sp.needs_reply === "false" ? false : undefined,
      date_from: sp.date_from,
      date_to: sp.date_to,
      limit: PAGINATION_SIZE,
      offset,
    }).catch(() => ({ total: 0, mails: [] })),
  ]);
  const mails = mailsRes.mails;
  const total = mailsRes.total;

  const hasFilter = !!(sp.q || sp.tag || sp.needs_reply || sp.date_from || sp.date_to);

  const prevHref = offset > 0 ? buildPageUrl(sp, Math.max(0, offset - PAGINATION_SIZE)) : null;
  const nextHref = offset + PAGINATION_SIZE < total ? buildPageUrl(sp, offset + PAGINATION_SIZE) : null;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <GoogleAuthBanner />
      <AppHeader actions={<><PipelineButton /><LogoutButton /></>} />

      <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        {/* 統計カード */}
        {stats ? (
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="総メール数" value={stats.total} />
            <StatCard label="未分析" value={stats.unanalyzed} alert={stats.unanalyzed > 0} />
            <StatCard label="返信必要" value={stats.needs_reply} alert={stats.needs_reply > 0} />
          </div>
        ) : (
          <p className="text-sm text-zinc-400">バックエンドに接続できませんでした</p>
        )}

        {/* メール一覧 */}
        <section className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <SectionTitle>
              {hasFilter ? `検索結果 ${total} 件` : "最近のメール"}
            </SectionTitle>
          </div>

          {/* 検索バー */}
          <Suspense>
            <MailSearchBar />
          </Suspense>

          <MailListTable
            mails={mails}
            total={total}
            offset={offset}
            paginationSize={PAGINATION_SIZE}
            prevHref={prevHref}
            nextHref={nextHref}
            hasFilter={hasFilter}
          />
        </section>
      </main>
    </div>
  );
}

function buildPageUrl(sp: SearchParams, offset: number): string {
  const p = new URLSearchParams();
  if (sp.q) p.set("q", sp.q);
  if (sp.tag) p.set("tag", sp.tag);
  if (sp.needs_reply) p.set("needs_reply", sp.needs_reply);
  if (sp.date_from) p.set("date_from", sp.date_from);
  if (sp.date_to) p.set("date_to", sp.date_to);
  if (offset) p.set("offset", String(offset));
  return `/?${p.toString()}`;
}

function StatCard({ label, value, alert = false }: { label: string; value: number; alert?: boolean }) {
  return (
    <div className={`bg-white dark:bg-zinc-800 rounded-xl border px-5 py-4 ${alert ? "border-orange-200 dark:border-orange-800" : "border-zinc-200 dark:border-zinc-700"}`}>
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className={`text-3xl font-semibold mt-1 ${alert ? "text-orange-500" : "text-zinc-900 dark:text-zinc-50"}`}>
        {value}
      </p>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
      {children}
    </h2>
  );
}
