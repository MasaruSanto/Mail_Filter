"use client";

import { useState, useTransition, useRef, useEffect } from "react";
import { replyMail, generateDraft } from "@/lib/api/mails";
import { getReplyTemplates, type ReplyTemplateItem } from "@/lib/api/auth";
import { transcribeSpeech } from "@/lib/api/speech";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

type Props = {
  mailId: string;
  defaultTo: string;
  defaultSubject: string;
  defaultBody: string;
  threadId?: string;
};

export default function ReplyForm({
  mailId,
  defaultTo,
  defaultSubject,
  defaultBody,
  threadId,
}: Props) {
  const [open, setOpen] = useState(false);
  const [to, setTo] = useState(defaultTo);
  const [subject, setSubject] = useState(defaultSubject);
  const [body, setBody] = useState(defaultBody);
  const [templates, setTemplates] = useState<ReplyTemplateItem[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [aiDraft, setAiDraft] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isPending, startTransition] = useTransition();

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);

  useEffect(() => {
    if (!open) setBody(defaultBody);
  }, [defaultBody]);

  async function handleOpen() {
    const token = getAuthToken();
    if (token) {
      try {
        setTemplates(await getReplyTemplates(token));
      } catch {
        setTemplates([]);
      }
    }
    setSelectedTemplateId("");
    setBody(defaultBody);
    setOpen(true);
  }

  function handleInsertTemplate(id: string) {
    setSelectedTemplateId(id);
    if (!id) return;
    const tmpl = templates.find((t) => t.id === id);
    if (!tmpl) return;
    setBody((prev) => prev + (prev ? "\n\n" : "") + tmpl.body);
  }

  async function handleGenerateDraft() {
    const token = getAuthToken();
    if (!token) return;
    setIsGenerating(true);
    setDraftError(null);
    setAiDraft(null);
    try {
      const res = await generateDraft(token, mailId);
      setAiDraft(res.draft);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : "AI生成に失敗しました");
    } finally {
      setIsGenerating(false);
    }
  }

  function handleInsertDraft() {
    if (!aiDraft) return;
    const tmpl = templates.find((t) => t.id === selectedTemplateId)?.body ?? "";
    const separator = aiDraft && tmpl ? "\n\n" : "";
    setBody(aiDraft + separator + tmpl);
    setAiDraft(null);
  }

  async function handleVoiceInput() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      return;
    }

    setError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("このブラウザはマイク入力に対応していません（HTTPSまたはlocalhost必須）");
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("マイクへのアクセスが拒否されました");
      return;
    }

    try {
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);
        setIsTranscribing(true);
        const token = getAuthToken();
        if (!token) { setIsTranscribing(false); return; }
        try {
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
          const text = await transcribeSpeech(token, blob);
          if (text) setBody((prev) => prev + (prev ? "\n" : "") + text);
        } catch (err) {
          setError(err instanceof Error ? err.message : "文字起こしに失敗しました");
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      stream.getTracks().forEach((t) => t.stop());
      setError(err instanceof Error ? err.message : "録音の開始に失敗しました");
    }
  }

  function handleSubmit() {
    setError(null);
    setSuccess(false);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) {
        setError("ログインが必要です");
        return;
      }
      try {
        await replyMail(token, mailId, { to, subject, body, thread_id: threadId });
        setSuccess(true);
        setOpen(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : "送信に失敗しました");
      }
    });
  }

  const inputClass =
    "w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

  return (
    <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xs font-medium text-zinc-400 uppercase tracking-widest">返信</h2>
        {success && <span className="text-xs text-green-600 dark:text-green-400">送信しました</span>}
      </div>

      {!open ? (
        <button
          onClick={handleOpen}
          className="w-full py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-600 text-sm text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700/50 transition-colors text-left px-4"
        >
          返信を作成する…
        </button>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} className="space-y-3">
          <div>
            <label className="block text-xs text-zinc-400 mb-1">宛先</label>
            <input type="email" required value={to} onChange={(e) => setTo(e.target.value)} className={inputClass} />
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1">件名</label>
            <input type="text" required value={subject} onChange={(e) => setSubject(e.target.value)} className={inputClass} />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs text-zinc-400">本文</label>
              <div className="flex items-center gap-2">
                {/* テンプレート挿入 */}
                {templates.length > 0 && (
                  <select
                    value={selectedTemplateId}
                    onChange={(e) => handleInsertTemplate(e.target.value)}
                    className="text-xs px-2 py-1 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-500 dark:text-zinc-400"
                  >
                    <option value="">テンプレートを挿入...</option>
                    {templates.map((t) => (
                      <option key={t.id} value={t.id}>{t.name}</option>
                    ))}
                  </select>
                )}
                {/* AI生成ボタン */}
                <button
                  type="button"
                  onClick={handleGenerateDraft}
                  disabled={isGenerating}
                  className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700/50 transition-colors disabled:opacity-50"
                >
                  {isGenerating ? (
                    <svg className="w-3.5 h-3.5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
                      <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                    </svg>
                  )}
                  {isGenerating ? "生成中..." : "AIで作成"}
                </button>

                {/* 音声入力ボタン */}
                <button
                  type="button"
                  onClick={handleVoiceInput}
                  disabled={isTranscribing}
                  title={isRecording ? "録音を停止して文字起こし" : "マイクで音声入力（Whisper）"}
                  className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border transition-colors disabled:opacity-50 ${
                    isRecording
                      ? "border-red-400 bg-red-50 dark:bg-red-900/30 text-red-500 dark:text-red-400 animate-pulse"
                      : "border-zinc-200 dark:border-zinc-600 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:border-zinc-300 dark:hover:border-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700/50"
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
                    <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
                    <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
                  </svg>
                  {isTranscribing ? "変換中..." : isRecording ? "停止して変換" : "音声入力"}
                </button>
              </div>
            </div>

            {/* AI生成プレビュー */}
            {draftError && <p className="text-xs text-red-500 mb-2">{draftError}</p>}
            {aiDraft && (
              <div className="mb-3 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-900/50 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-200 dark:border-zinc-600">
                  <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
                      <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
                    </svg>
                    AI生成草稿
                  </span>
                  <div className="flex items-center gap-2">
                    <button type="button" onClick={handleInsertDraft} className="text-xs px-2.5 py-1 rounded-md bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors">
                      本文に挿入
                    </button>
                    <button type="button" onClick={() => setAiDraft(null)} className="text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors">✕</button>
                  </div>
                </div>
                <div className="px-3 py-3 text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">{aiDraft}</div>
                {selectedTemplateId && (
                  <>
                    <div className="px-3 border-t border-zinc-200 dark:border-zinc-600 py-1.5">
                      <span className="text-xs text-zinc-400">テンプレート</span>
                    </div>
                    <div className="px-3 pb-3 text-sm text-zinc-500 dark:text-zinc-400 whitespace-pre-wrap">
                      {templates.find((t) => t.id === selectedTemplateId)?.body}
                    </div>
                  </>
                )}
              </div>
            )}

            <textarea
              required
              rows={15}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className={`${inputClass} resize-y`}
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-2 justify-end pt-1">
            <button
              type="button"
              onClick={() => setOpen(false)}
              disabled={isPending}
              className="text-sm px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
            >
              キャンセル
            </button>
            <button
              type="submit"
              disabled={isPending || !to || !subject || !body}
              className="text-sm px-5 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isPending ? "送信中..." : "送信"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
