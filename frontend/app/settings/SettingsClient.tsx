"use client";

import { useState, useTransition, useEffect } from "react";
import {
  changePassword, getGoogleAuthUrl,
  getReplyTemplates, createReplyTemplate, updateReplyTemplateItem, deleteReplyTemplateItem,
  type ReplyTemplateItem,
  getPromptSetting, updatePromptSetting,
  getPipelineSchedule, updatePipelineSchedule,
  getLlmSetting, updateLlmSetting,
  getSlackSetting, updateSlackSetting,
  getWeeklyReportSetting, updateWeeklyReportSetting, sendWeeklyReportNow,
} from "@/lib/api/auth";
import type { UserOut } from "@/lib/types/api";

export const PIPELINE_MAX_RESULTS_KEY = "pipeline_max_results";
export const PIPELINE_AFTER_DAYS_KEY  = "pipeline_after_days";

const MAX_RESULTS_OPTIONS = [5, 10, 20, 50];
const DATE_RANGE_OPTIONS: { label: string; value: number | null }[] = [
  { label: "7日",  value: 7  },
  { label: "1か月", value: 30 },
  { label: "3か月", value: 90 },
  { label: "無制限", value: null },
];

// ─── アイコン ───────────────────────────────────────────
function IconUser() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
      strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
    </svg>
  );
}
function IconMail() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
      strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
    </svg>
  );
}
function IconSparkles() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
      strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
    </svg>
  );
}

const OPENAI_MODELS = [
  { label: "gpt-5-nano",  value: "gpt-5-nano"  },
  { label: "gpt-4o-mini", value: "gpt-4o-mini" },
  { label: "gpt-4o",      value: "gpt-4o"      },
  { label: "gpt-4-turbo", value: "gpt-4-turbo" },
];

function IconBell() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
      strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 shrink-0">
      <path strokeLinecap="round" strokeLinejoin="round"
        d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
    </svg>
  );
}

// ─── タブ定義 ────────────────────────────────────────────
type TabId = "account" | "mail" | "ai" | "notify";
const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "account", label: "アカウント",  icon: <IconUser />      },
  { id: "mail",    label: "メール取得",  icon: <IconMail />      },
  { id: "ai",      label: "AI・返信",    icon: <IconSparkles />  },
  { id: "notify",  label: "通知",        icon: <IconBell />      },
];

// ─── 共通パーツ ──────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-widest mb-4">
      {children}
    </h3>
  );
}

function SaveButton({
  onClick, saving, saved, disabled,
}: {
  onClick: () => void; saving?: boolean; saved: boolean; disabled?: boolean;
}) {
  return (
    <div className="flex items-center justify-end gap-3 pt-1">
      {saved && <span className="text-xs text-green-600 dark:text-green-400">保存しました</span>}
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className="text-sm px-4 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {saving ? "保存中..." : "保存する"}
      </button>
    </div>
  );
}

function ToggleGroup({
  options, value, onChange,
}: {
  options: { label: string; value: number | null }[];
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-600 overflow-hidden">
      {options.map((opt) => (
        <button
          key={String(opt.value)}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-4 py-2 text-sm transition-colors ${
            value === opt.value
              ? "bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium"
              : "text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

const inputClass =
  "w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

// ─── メインコンポーネント ────────────────────────────────
export default function SettingsClient({ user, token }: { user: UserOut; token: string }) {
  const [activeTab, setActiveTab] = useState<TabId>("account");

  // パスワード
  const [current, setCurrent]     = useState("");
  const [next, setNext]           = useState("");
  const [confirm, setConfirm]     = useState("");
  const [pwError, setPwError]     = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [isPwPending, startPwTransition] = useTransition();

  // メール取得
  const [maxResults, setMaxResults]   = useState(10);
  const [afterDays, setAfterDays]     = useState<number | null>(30);
  const [scheduleMinutes, setScheduleMinutes] = useState<number | null>(30);
  const [scheduleSaved, setScheduleSaved]     = useState(false);

  // Google
  const [connecting, setConnecting] = useState(false);

  // 返信テンプレート（複数管理）
  const [templates, setTemplates] = useState<ReplyTemplateItem[]>([]);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [editingTemplateId, setEditingTemplateId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [isAddingTemplate, setIsAddingTemplate] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);

  // AI指示
  const [promptInstruction, setPromptInstruction] = useState("");
  const [promptSaved, setPromptSaved]             = useState(false);

  // LLMモデル設定
  const [llmProvider, setLlmProvider] = useState<"local" | "openai">("local");
  const [llmModel, setLlmModel]       = useState("gpt-4o-mini");
  const [llmApiKey, setLlmApiKey]     = useState("");
  const [llmSaved, setLlmSaved]       = useState(false);

  // Slack通知設定
  const [slackBotToken, setSlackBotToken]   = useState("");
  const [slackChannelId, setSlackChannelId] = useState("");
  const [slackHasToken, setSlackHasToken]   = useState(false);
  const [slackSaved, setSlackSaved]         = useState(false);

  // 週次レポート設定
  const [weeklyReportEnabled, setWeeklyReportEnabled] = useState(false);
  const [weeklyReportSaved, setWeeklyReportSaved]     = useState(false);
  const [sendingNow, setSendingNow]                   = useState(false);
  const [sendNowError, setSendNowError]               = useState<string | null>(null);
  const [sendNowSuccess, setSendNowSuccess]           = useState(false);

  useEffect(() => {
    const savedMax  = localStorage.getItem(PIPELINE_MAX_RESULTS_KEY);
    const savedDays = localStorage.getItem(PIPELINE_AFTER_DAYS_KEY);
    if (savedMax)  setMaxResults(Number(savedMax));
    if (savedDays !== null) setAfterDays(savedDays === "null" ? null : Number(savedDays));

    getReplyTemplates(token)
      .then(setTemplates)
      .catch(() => {});
    getPromptSetting(token)
      .then(({ prompt_instruction }) => { if (prompt_instruction) setPromptInstruction(prompt_instruction); })
      .catch(() => {});
    getLlmSetting(token)
      .then(({ provider, model }) => {
        setLlmProvider(provider as "local" | "openai");
        if (model) setLlmModel(model);
      })
      .catch(() => {});
    getPipelineSchedule(token)
      .then(({ interval_minutes }) => { setScheduleMinutes(interval_minutes ?? 30); })
      .catch(() => {});
    getSlackSetting(token)
      .then(({ channel_id, has_token }) => {
        if (channel_id) setSlackChannelId(channel_id);
        setSlackHasToken(has_token);
      })
      .catch(() => {});
    getWeeklyReportSetting(token)
      .then(({ enabled }) => setWeeklyReportEnabled(enabled))
      .catch(() => {});
  }, [token]);

  function handleMaxResultsChange(val: number | null) {
    if (val === null) return;
    setMaxResults(val);
    localStorage.setItem(PIPELINE_MAX_RESULTS_KEY, String(val));
  }
  function handleAfterDaysChange(val: number | null) {
    setAfterDays(val);
    localStorage.setItem(PIPELINE_AFTER_DAYS_KEY, String(val));
  }

  function startAddTemplate() {
    setIsAddingTemplate(true);
    setEditingTemplateId(null);
    setDraftName("");
    setDraftBody("");
    setTemplatesError(null);
  }
  function startEditTemplate(t: ReplyTemplateItem) {
    setEditingTemplateId(t.id);
    setIsAddingTemplate(false);
    setDraftName(t.name);
    setDraftBody(t.body);
    setTemplatesError(null);
  }
  function cancelTemplateEdit() {
    setIsAddingTemplate(false);
    setEditingTemplateId(null);
  }
  async function handleTemplateSave() {
    if (!draftName.trim() || !draftBody.trim()) {
      setTemplatesError("名前と本文を入力してください");
      return;
    }
    setSavingTemplate(true);
    setTemplatesError(null);
    try {
      if (editingTemplateId) {
        const updated = await updateReplyTemplateItem(token, editingTemplateId, { name: draftName, body: draftBody });
        setTemplates((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      } else {
        const created = await createReplyTemplate(token, { name: draftName, body: draftBody });
        setTemplates((prev) => [...prev, created]);
      }
      setIsAddingTemplate(false);
      setEditingTemplateId(null);
    } catch (err) {
      setTemplatesError(err instanceof Error ? err.message : "保存に失敗しました");
    } finally {
      setSavingTemplate(false);
    }
  }
  async function handleTemplateDelete(id: string) {
    setTemplatesError(null);
    try {
      await deleteReplyTemplateItem(token, id);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setTemplatesError(err instanceof Error ? err.message : "削除に失敗しました");
    }
  }
  async function handlePromptSave() {
    await updatePromptSetting(token, promptInstruction).catch(() => {});
    setPromptSaved(true);
    setTimeout(() => setPromptSaved(false), 2000);
  }
  async function handleLlmSave() {
    await updateLlmSetting(token, {
      provider: llmProvider,
      ...(llmProvider === "openai" && llmApiKey ? { api_key: llmApiKey } : {}),
      model: llmModel,
    }).catch(() => {});
    setLlmApiKey("");
    setLlmSaved(true);
    setTimeout(() => setLlmSaved(false), 2000);
  }
  async function handleScheduleSave() {
    await updatePipelineSchedule(token, scheduleMinutes).catch(() => {});
    setScheduleSaved(true);
    setTimeout(() => setScheduleSaved(false), 2000);
  }

  async function handleSlackSave() {
    const body: { bot_token?: string; channel_id?: string } = {};
    if (slackBotToken) body.bot_token = slackBotToken;
    if (slackChannelId !== undefined) body.channel_id = slackChannelId;
    await updateSlackSetting(token, body).catch(() => {});
    if (slackBotToken) {
      setSlackHasToken(true);
      setSlackBotToken("");
    }
    setSlackSaved(true);
    setTimeout(() => setSlackSaved(false), 2000);
  }

  async function handleWeeklyReportToggle(enabled: boolean) {
    setWeeklyReportEnabled(enabled);
    await updateWeeklyReportSetting(token, enabled).catch(() => {});
    setWeeklyReportSaved(true);
    setTimeout(() => setWeeklyReportSaved(false), 2000);
  }

  async function handleSendNow() {
    setSendingNow(true);
    setSendNowError(null);
    setSendNowSuccess(false);
    try {
      await sendWeeklyReportNow(token);
      setSendNowSuccess(true);
      setTimeout(() => setSendNowSuccess(false), 3000);
    } catch (err) {
      setSendNowError(err instanceof Error ? err.message : "送信に失敗しました");
    } finally {
      setSendingNow(false);
    }
  }

  async function handleGoogleConnect() {
    setConnecting(true);
    try {
      const { url } = await getGoogleAuthUrl(token);
      window.location.href = url;
    } catch { setConnecting(false); }
  }

  function handlePasswordSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);
    if (next !== confirm) { setPwError("新しいパスワードが一致しません"); return; }
    startPwTransition(async () => {
      try {
        await changePassword(token, { current_password: current, new_password: next });
        setPwSuccess(true);
        setCurrent(""); setNext(""); setConfirm("");
      } catch (err) {
        setPwError(err instanceof Error ? err.message : "変更に失敗しました");
      }
    });
  }

  // ─── タブコンテンツ ────────────────────────────────────
  const content: Record<TabId, React.ReactNode> = {
    notify: (
      <div className="space-y-6">
        <div>
          <SectionTitle>週次メールサマリーレポート</SectionTitle>
          <p className="text-xs text-zinc-400 mb-4">
            毎週月曜9:00に、直近7日間のメール件数・要返信件数・TODO生成数などをまとめて自分のメールアドレスに送信します。
          </p>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-700 dark:text-zinc-300">自動送信</p>
                <p className="text-xs text-zinc-400 mt-0.5">Google連携が必要です</p>
              </div>
              <ToggleGroup
                value={weeklyReportEnabled ? 1 : 0}
                onChange={(v) => handleWeeklyReportToggle(v === 1)}
                options={[
                  { label: "無効", value: 0 },
                  { label: "有効", value: 1 },
                ]}
              />
            </div>
            <div className="flex items-center justify-end gap-3">
              {weeklyReportSaved && <span className="text-xs text-green-600 dark:text-green-400">保存しました</span>}
              {sendNowSuccess && <span className="text-xs text-green-600 dark:text-green-400">送信しました</span>}
              {sendNowError && <span className="text-xs text-red-500">{sendNowError}</span>}
              <button
                type="button"
                onClick={handleSendNow}
                disabled={sendingNow}
                className="text-sm px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                {sendingNow ? "送信中..." : "今すぐ送信（テスト）"}
              </button>
            </div>
          </div>
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        <div>
          <SectionTitle>Slack通知</SectionTitle>
          <p className="text-xs text-zinc-400 mb-4">
            要返信メールが検出されたとき、指定のSlackチャンネルに通知します。
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">
                Bot Token
                {slackHasToken && (
                  <span className="ml-2 text-green-600 dark:text-green-400">設定済み</span>
                )}
                <span className="ml-1 text-zinc-300">（変更する場合のみ入力）</span>
              </label>
              <input
                type="password"
                value={slackBotToken}
                onChange={(e) => setSlackBotToken(e.target.value)}
                placeholder="xoxb-..."
                className={inputClass}
              />
              <p className="text-xs text-zinc-400 mt-1">
                Slack App の「OAuth &amp; Permissions」から取得した Bot User OAuth Token
              </p>
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">チャンネルID</label>
              <input
                type="text"
                value={slackChannelId}
                onChange={(e) => setSlackChannelId(e.target.value)}
                placeholder="C0XXXXXXX"
                className={inputClass}
              />
              <p className="text-xs text-zinc-400 mt-1">
                チャンネル名ではなくID（チャンネルを右クリック→「リンクをコピー」の末尾部分）
              </p>
            </div>
            <SaveButton onClick={handleSlackSave} saved={slackSaved} />
          </div>
        </div>
      </div>
    ),

    account: (
      <div className="space-y-6">
        {/* アカウント情報 */}
        <div>
          <SectionTitle>アカウント情報</SectionTitle>
          <dl className="space-y-3 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-zinc-100 dark:border-zinc-700">
              <dt className="text-zinc-400">メールアドレス</dt>
              <dd className="text-zinc-700 dark:text-zinc-300 font-medium">{user.email}</dd>
            </div>
            <div className="flex items-center justify-between py-2">
              <dt className="text-zinc-400">登録日</dt>
              <dd className="text-zinc-500 dark:text-zinc-400">{user.created_at.slice(0, 10)}</dd>
            </div>
          </dl>
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        {/* Google連携 */}
        <div>
          <SectionTitle>Google連携</SectionTitle>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-zinc-700 dark:text-zinc-300">Gmail / Google カレンダー</p>
              <p className="text-xs text-zinc-400 mt-0.5">メール取得・カレンダー操作に必要です</p>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                user.google_authorized
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-zinc-100 text-zinc-500 dark:bg-zinc-700 dark:text-zinc-400"
              }`}>
                {user.google_authorized ? "連携済み" : "未連携"}
              </span>
              <button
                onClick={handleGoogleConnect}
                disabled={connecting}
                className="text-sm px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
              >
                {connecting ? "接続中..." : user.google_authorized ? "再連携" : "連携する"}
              </button>
            </div>
          </div>
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        {/* パスワード変更 */}
        <div>
          <SectionTitle>パスワード変更</SectionTitle>
          <form onSubmit={handlePasswordSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-zinc-400 mb-1">現在のパスワード</label>
              <input type="password" required autoComplete="current-password"
                value={current} onChange={(e) => setCurrent(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">新しいパスワード</label>
              <input type="password" required autoComplete="new-password"
                value={next} onChange={(e) => setNext(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1">新しいパスワード（確認）</label>
              <input type="password" required autoComplete="new-password"
                value={confirm} onChange={(e) => setConfirm(e.target.value)} className={inputClass} />
            </div>
            {pwError   && <p className="text-xs text-red-500">{pwError}</p>}
            {pwSuccess && <p className="text-xs text-green-600 dark:text-green-400">パスワードを変更しました</p>}
            <div className="flex justify-end pt-1">
              <button
                type="submit"
                disabled={isPwPending || !current || !next || !confirm}
                className="text-sm px-4 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPwPending ? "変更中..." : "変更する"}
              </button>
            </div>
          </form>
        </div>
      </div>
    ),

    mail: (
      <div className="space-y-6">
        {/* パイプライン自動実行 */}
        <div>
          <SectionTitle>パイプライン自動実行</SectionTitle>
          <p className="text-xs text-zinc-400 mb-4">
            設定した間隔で自動的にメールを取得・分析します。サーバー起動中のみ有効です。
          </p>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-700 dark:text-zinc-300">実行間隔</p>
              <ToggleGroup
                value={scheduleMinutes}
                onChange={setScheduleMinutes}
                options={[
                  { label: "5分",  value: 5  },
                  { label: "10分", value: 10 },
                  { label: "30分", value: 30 },
                  { label: "1時間", value: 60 },
                  { label: "無効", value: null },
                ]}
              />
            </div>
            <SaveButton onClick={handleScheduleSave} saved={scheduleSaved} />
          </div>
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        {/* メール取得設定 */}
        <div>
          <SectionTitle>メール取得設定</SectionTitle>
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-700 dark:text-zinc-300">1回の取得件数</p>
                <p className="text-xs text-zinc-400 mt-0.5">手動実行で一度に処理する件数</p>
              </div>
              <ToggleGroup
                value={maxResults}
                onChange={handleMaxResultsChange}
                options={MAX_RESULTS_OPTIONS.map((n) => ({ label: String(n), value: n }))}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-700 dark:text-zinc-300">取得期間</p>
                <p className="text-xs text-zinc-400 mt-0.5">この期間より新しいメールのみ取得</p>
              </div>
              <ToggleGroup
                value={afterDays}
                onChange={handleAfterDaysChange}
                options={DATE_RANGE_OPTIONS}
              />
            </div>
          </div>
        </div>
      </div>
    ),

    ai: (
      <div className="space-y-6">
        {/* LLMモデル設定 */}
        <div>
          <SectionTitle>LLMモデル設定</SectionTitle>
          <p className="text-xs text-zinc-400 mb-4">
            メール分類・要約・返信文生成に使用するモデルを選択してください。
          </p>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-zinc-700 dark:text-zinc-300">プロバイダー</p>
              <ToggleGroup
                value={llmProvider === "openai" ? 1 : 0}
                onChange={(v) => setLlmProvider(v === 1 ? "openai" : "local")}
                options={[
                  { label: "ローカルLLM", value: 0 },
                  { label: "ChatGPT API", value: 1 },
                ]}
              />
            </div>
            {llmProvider === "openai" && (
              <>
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">モデル</label>
                  <div className="flex rounded-lg border border-zinc-200 dark:border-zinc-600 overflow-hidden">
                    {OPENAI_MODELS.map((m) => (
                      <button
                        key={m.value}
                        type="button"
                        onClick={() => setLlmModel(m.value)}
                        className={`flex-1 px-4 py-2 text-sm transition-colors ${
                          llmModel === m.value
                            ? "bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium"
                            : "text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700"
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-zinc-400 mb-1">
                    APIキー
                    <span className="ml-1 text-zinc-300">（変更する場合のみ入力）</span>
                  </label>
                  <input
                    type="password"
                    value={llmApiKey}
                    onChange={(e) => setLlmApiKey(e.target.value)}
                    placeholder="sk-..."
                    className={inputClass}
                  />
                </div>
              </>
            )}
            <SaveButton onClick={handleLlmSave} saved={llmSaved} />
          </div>
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        {/* 返信テンプレート（複数管理） */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <SectionTitle>返信テンプレート</SectionTitle>
            {!isAddingTemplate && !editingTemplateId && (
              <button
                type="button"
                onClick={startAddTemplate}
                className="text-xs px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
              >
                + 新規追加
              </button>
            )}
          </div>
          <p className="text-xs text-zinc-400 mb-3">
            返信フォームでクライアント・用途別に選んで挿入できます
          </p>

          <div className="space-y-2">
            {templates.length === 0 && !isAddingTemplate && (
              <p className="text-sm text-zinc-400">テンプレートはまだありません</p>
            )}
            {templates.map((t) =>
              editingTemplateId === t.id ? (
                <div key={t.id} className="rounded-lg border border-zinc-200 dark:border-zinc-600 p-3 space-y-2">
                  <input
                    type="text"
                    value={draftName}
                    onChange={(e) => setDraftName(e.target.value)}
                    placeholder="テンプレート名（例：クライアントA向け）"
                    className={inputClass}
                  />
                  <textarea
                    rows={5}
                    value={draftBody}
                    onChange={(e) => setDraftBody(e.target.value)}
                    className={`${inputClass} resize-y font-mono`}
                  />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={cancelTemplateEdit}
                      className="text-xs px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors">
                      キャンセル
                    </button>
                    <button type="button" onClick={handleTemplateSave} disabled={savingTemplate}
                      className="text-xs px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50">
                      {savingTemplate ? "保存中..." : "保存"}
                    </button>
                  </div>
                </div>
              ) : (
                <div key={t.id} className="flex items-start justify-between gap-3 rounded-lg border border-zinc-200 dark:border-zinc-600 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{t.name}</p>
                    <p className="text-xs text-zinc-400 mt-0.5 line-clamp-2 whitespace-pre-wrap">{t.body}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button type="button" onClick={() => startEditTemplate(t)}
                      className="text-xs text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors">
                      編集
                    </button>
                    <button type="button" onClick={() => handleTemplateDelete(t.id)}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors">
                      削除
                    </button>
                  </div>
                </div>
              )
            )}

            {isAddingTemplate && (
              <div className="rounded-lg border border-zinc-200 dark:border-zinc-600 p-3 space-y-2">
                <input
                  type="text"
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  placeholder="テンプレート名（例：クライアントA向け）"
                  className={inputClass}
                />
                <textarea
                  rows={5}
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                  placeholder={"例：\n\nよろしくお願いいたします。\n\n山田 太郎\n株式会社〇〇"}
                  className={`${inputClass} resize-y font-mono`}
                />
                <div className="flex justify-end gap-2">
                  <button type="button" onClick={cancelTemplateEdit}
                    className="text-xs px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors">
                    キャンセル
                  </button>
                  <button type="button" onClick={handleTemplateSave} disabled={savingTemplate}
                    className="text-xs px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-50">
                    {savingTemplate ? "保存中..." : "追加"}
                  </button>
                </div>
              </div>
            )}
          </div>
          {templatesError && <p className="text-xs text-red-500 mt-2">{templatesError}</p>}
        </div>

        <hr className="border-zinc-100 dark:border-zinc-700" />

        {/* AI分類の追加指示 */}
        <div>
          <SectionTitle>AI分類の追加指示</SectionTitle>
          <p className="text-xs text-zinc-400 mb-2">
            メール分類時に LLM へ追加で渡すルールを入力してください。
          </p>
          <ul className="text-xs text-zinc-500 dark:text-zinc-400 list-disc list-inside space-y-0.5 mb-3">
            <li>営業メールはすべて迷惑メールとして分類してください</li>
            <li>@example.com からのメールは社内メールとして扱ってください</li>
            <li>返信期限が3日以内のメールは緊急メールに分類してください</li>
          </ul>
          <textarea
            rows={5}
            value={promptInstruction}
            onChange={(e) => setPromptInstruction(e.target.value)}
            placeholder="追加指示を入力（空欄の場合はデフォルトのルールのみ適用されます）"
            className={`${inputClass} resize-y font-mono`}
          />
          <SaveButton onClick={handlePromptSave} saved={promptSaved} />
        </div>
      </div>
    ),
  };

  // ─── レイアウト ───────────────────────────────────────
  return (
    <div className="flex flex-col lg:flex-row gap-6 items-start">

      {/* サイドバー（lg以上）/ 横タブ（モバイル） */}
      <nav className="w-full lg:w-44 shrink-0">
        {/* モバイル: 横並びタブ */}
        <div className="flex lg:hidden gap-1 p-1 bg-zinc-100 dark:bg-zinc-800 rounded-xl">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 shadow-sm"
                  : "text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* デスクトップ: 縦サイドバー */}
        <ul className="hidden lg:flex flex-col gap-0.5">
          {TABS.map((tab) => (
            <li key={tab.id}>
              <button
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  activeTab === tab.id
                    ? "bg-zinc-900 dark:bg-zinc-100 text-zinc-50 dark:text-zinc-900 font-medium"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* コンテンツパネル */}
      <div className="flex-1 min-w-0 bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
        {content[activeTab]}
      </div>

    </div>
  );
}
