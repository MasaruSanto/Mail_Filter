import { getMail } from "@/lib/api/mails";
import { notFound, redirect } from "next/navigation";
import { cookies } from "next/headers";
import Link from "next/link";
import AppHeader from "@/app/_components/AppHeader";
import LogoutButton from "@/app/_components/LogoutButton";
import ReplyForm from "./ReplyForm";
import AnalyzeButton from "./AnalyzeButton";
import DeleteMailButton from "./DeleteMailButton";
import AttachmentList from "./AttachmentList";
import type { Priority } from "@/lib/types/api";

const PRIORITY_COLOR: Record<Priority, string> = {
  "迷惑メール": "bg-red-100 text-red-700",
  "業務メール": "bg-blue-100 text-blue-700",
  "営業メール": "bg-yellow-100 text-yellow-700",
  "個人メール": "bg-green-100 text-green-700",
  "緊急メール": "bg-red-100 text-red-800 font-semibold",
  "返信必要": "bg-orange-100 text-orange-700",
  "対応待ち": "bg-zinc-100 text-zinc-600",
  "社内メール": "bg-purple-100 text-purple-700",
};

export default async function MailDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("auth_token")?.value;
  if (!token) redirect("/login");

  const mail = await getMail(token, id).catch(() => null);
  if (!mail) notFound();

  const a = mail.assessment;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AppHeader actions={<LogoutButton />} />

      <main className="max-w-6xl mx-auto px-6 py-8 space-y-5">
        {/* 戻るリンク */}
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
        >
          ← ダッシュボードへ戻る
        </Link>

        {/* 2カラムグリッド */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_500px] gap-5 items-start">

          {/* ─── 左カラム：メール本体 ─── */}
          <div className="space-y-5">
            {/* メールヘッダー */}
            <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 leading-snug">
                  {mail.title ?? "（件名なし）"}
                </h1>
                <div className="flex items-center gap-2 shrink-0">
                  {mail.has_attachments && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400">
                      添付あり
                    </span>
                  )}
                  {a?.priority && (
                    <span className={`text-xs px-2 py-0.5 rounded-full ${PRIORITY_COLOR[a.priority as Priority]}`}>
                      {a.priority}
                    </span>
                  )}
                  {!mail.is_analyzed && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-400 dark:bg-zinc-700">
                      未分析
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between gap-2">
                {!mail.is_analyzed && <AnalyzeButton mailId={id} />}
                <div className="ml-auto">
                  <DeleteMailButton mailId={id} />
                </div>
              </div>

              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
                <dt className="text-zinc-400 whitespace-nowrap">送信者</dt>
                <dd className="text-zinc-700 dark:text-zinc-300">
                  {mail.from_name ? (
                    <>
                      {mail.from_name}{" "}
                      {mail.from_email && (
                        <span className="text-zinc-400">&lt;{mail.from_email}&gt;</span>
                      )}
                    </>
                  ) : (
                    mail.from_email ?? "—"
                  )}
                </dd>

                <dt className="text-zinc-400 whitespace-nowrap">宛先</dt>
                <dd className="text-zinc-700 dark:text-zinc-300">
                  {mail.to_name ? (
                    <>
                      {mail.to_name}{" "}
                      {mail.to_email && (
                        <span className="text-zinc-400">&lt;{mail.to_email}&gt;</span>
                      )}
                    </>
                  ) : (
                    mail.to_email ?? "—"
                  )}
                </dd>

                <dt className="text-zinc-400 whitespace-nowrap">日付</dt>
                <dd suppressHydrationWarning className="text-zinc-700 dark:text-zinc-300">{mail.day ?? "—"}</dd>
              </dl>
            </div>

            {/* メール本文 */}
            <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
              <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-4">
                本文
              </h2>
              {mail.body ? (
                <pre className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap break-words font-sans leading-relaxed">
                  {mail.body}
                </pre>
              ) : (
                <p className="text-sm text-zinc-400">本文がありません</p>
              )}
            </div>

            <AttachmentList mailId={id} attachments={mail.attachments} />
          </div>

          {/* ─── 右カラム：AI分析 + 返信 ─── */}
          <div className="space-y-5 lg:sticky lg:top-6">
            {/* AI分析結果 */}
            {a && (
              <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6 space-y-4">
                <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest">
                  AI分析結果
                </h2>

                <dl className="space-y-3 text-sm">
                  <div>
                    <dt className="text-xs text-zinc-400 mb-1">要約</dt>
                    <dd className="text-zinc-800 dark:text-zinc-200 leading-relaxed">
                      {a.summarized_body}
                    </dd>
                  </div>

                  {a.reason && (
                    <div>
                      <dt className="text-xs text-zinc-400 mb-1">判定理由</dt>
                      <dd className="text-zinc-600 dark:text-zinc-400">{a.reason}</dd>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-4">
                    <div>
                      <dt className="text-xs text-zinc-400 mb-1">返信</dt>
                      <dd>
                        {a.replied_at ? (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400 font-medium">
                            ✓ 返信済み
                          </span>
                        ) : a.needs_immediate_reply ? (
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-400 font-medium">
                            返信必要
                          </span>
                        ) : (
                          <span className="text-xs text-zinc-400">不要</span>
                        )}
                      </dd>
                    </div>

                    {a.extracted_deadline && (
                      <div>
                        <dt className="text-xs text-zinc-400 mb-1">期限</dt>
                        <dd suppressHydrationWarning className="text-zinc-700 dark:text-zinc-300">
                          {a.extracted_deadline.slice(0, 16).replace("T", " ")}
                        </dd>
                      </div>
                    )}

                    <div>
                      <dt className="text-xs text-zinc-400 mb-1">分析日時</dt>
                      <dd suppressHydrationWarning className="text-zinc-400 text-xs">
                        {a.assessed_at.slice(0, 16).replace("T", " ")}
                      </dd>
                    </div>

                    {a.replied_at && (
                      <div>
                        <dt className="text-xs text-zinc-400 mb-1">返信日時</dt>
                        <dd suppressHydrationWarning className="text-zinc-400 text-xs">
                          {a.replied_at.slice(0, 16).replace("T", " ")}
                        </dd>
                      </div>
                    )}
                  </div>

                </dl>
              </div>
            )}

            {/* 返信フォーム */}
            <ReplyForm
              key={a?.assessed_at ?? "no-assessment"}
              mailId={id}
              defaultTo={mail.from_email ?? ""}
              defaultSubject={mail.title ? `Re: ${mail.title}` : "Re:"}
              defaultBody={a?.ai_response_message ?? ""}
            />
          </div>

        </div>
      </main>
    </div>
  );
}
