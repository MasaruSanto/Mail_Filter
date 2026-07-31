"use client";

import { useState, useEffect, useRef, useTransition } from "react";
import { useRouter } from "next/navigation";
import { sendMail } from "@/lib/api/mails";
import { getContacts } from "@/lib/api/contacts";
import type { Contact } from "@/lib/api/contacts";
import AppHeader from "@/app/_components/AppHeader";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const inputClass =
  "w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50 text-sm focus:outline-none focus:ring-2 focus:ring-zinc-400";

type SelectedContact = { name: string; email: string };

export default function ComposePage() {
  const router = useRouter();
  // 選択済み宛先（チップ表示用）
  const [selectedContact, setSelectedContact] = useState<SelectedContact | null>(null);
  // 手動入力バッファ（未選択時）
  const [toInput, setToInput] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [isPending, startTransition] = useTransition();

  // 宛先オートコンプリート
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [suggestions, setSuggestions] = useState<Contact[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const toWrapperRef = useRef<HTMLDivElement>(null);
  const toInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;
    getContacts(token)
      .then(setContacts)
      .catch(() => {});
  }, []);

  // サジェスト外クリックで閉じる
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (toWrapperRef.current && !toWrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleToInputChange(value: string) {
    setToInput(value);
    if (value.length >= 1) {
      const q = value.toLowerCase();
      const filtered = contacts.filter(
        (c) => c.email.toLowerCase().includes(q) || c.name.toLowerCase().includes(q)
      );
      setSuggestions(filtered.slice(0, 8));
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }

  function handleSelectContact(contact: Contact) {
    setSelectedContact({ name: contact.name || contact.email, email: contact.email });
    setToInput("");
    setShowSuggestions(false);
  }

  function handleRemoveContact() {
    setSelectedContact(null);
    setToInput("");
    setTimeout(() => toInputRef.current?.focus(), 0);
  }

  // 送信時の宛先：選択済みチップ優先、なければ手動入力値
  const toEmail = selectedContact?.email ?? toInput;

  function handleSubmit() {
    setError(null);
    startTransition(async () => {
      const token = getAuthToken();
      if (!token) {
        setError("ログインが必要です");
        return;
      }
      try {
        await sendMail(token, { to: toEmail, subject, body });
        setSuccess(true);
        setTimeout(() => router.push("/"), 1500);
      } catch (err) {
        setError(err instanceof Error ? err.message : "送信に失敗しました");
      }
    });
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900">
      <AppHeader />
      <main className="max-w-2xl mx-auto px-6 py-10">
        <div className="bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-zinc-700 p-6">
          <h1 className="text-sm font-semibold text-zinc-700 dark:text-zinc-200 mb-6">新規メール作成</h1>

          {success ? (
            <p className="text-sm text-green-600 dark:text-green-400 text-center py-8">
              送信しました。ダッシュボードに戻ります…
            </p>
          ) : (
            <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} className="space-y-4">

              {/* 宛先 */}
              <div ref={toWrapperRef} className="relative">
                <label className="block text-xs text-zinc-400 mb-1">宛先</label>
                <div
                  className="flex flex-wrap items-center gap-1.5 min-h-[38px] px-2 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-zinc-700 focus-within:ring-2 focus-within:ring-zinc-400"
                  onClick={() => toInputRef.current?.focus()}
                >
                  {/* 選択済みチップ */}
                  {selectedContact && (
                    <span className="inline-flex items-center gap-1 text-xs bg-zinc-100 dark:bg-zinc-600 text-zinc-800 dark:text-zinc-100 px-2 py-1 rounded-md">
                      <span className="font-medium">{selectedContact.name}</span>
                      <span className="text-zinc-400 dark:text-zinc-400 text-[11px]">
                        {selectedContact.email}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleRemoveContact(); }}
                        className="ml-0.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 leading-none"
                      >
                        ✕
                      </button>
                    </span>
                  )}

                  {/* テキスト入力（チップ未選択時のみ入力可） */}
                  {!selectedContact && (
                    <input
                      ref={toInputRef}
                      type="text"
                      value={toInput}
                      onChange={(e) => handleToInputChange(e.target.value)}
                      onFocus={() => toInput.length >= 1 && setShowSuggestions(suggestions.length > 0)}
                      placeholder="名前またはメールアドレスを入力"
                      className="flex-1 min-w-[180px] bg-transparent text-sm text-zinc-900 dark:text-zinc-50 outline-none placeholder:text-zinc-400"
                      autoComplete="off"
                    />
                  )}
                </div>

                {/* サジェストドロップダウン */}
                {showSuggestions && (
                  <div className="absolute z-10 w-full mt-1 bg-white dark:bg-zinc-700 border border-zinc-200 dark:border-zinc-600 rounded-lg shadow-lg overflow-hidden">
                    {suggestions.map((c) => (
                      <button
                        key={c.email}
                        type="button"
                        onMouseDown={() => handleSelectContact(c)}
                        className="w-full text-left px-3 py-2.5 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-600 transition-colors flex items-center gap-2"
                      >
                        <span className="w-7 h-7 rounded-full bg-zinc-200 dark:bg-zinc-500 flex items-center justify-center text-xs font-medium text-zinc-600 dark:text-zinc-200 shrink-0">
                          {(c.name || c.email)[0].toUpperCase()}
                        </span>
                        <span>
                          <span className="block text-zinc-800 dark:text-zinc-100">
                            {c.name || c.email}
                          </span>
                          {c.name && (
                            <span className="block text-xs text-zinc-400">{c.email}</span>
                          )}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* 件名 */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">件名</label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="件名を入力"
                  className={inputClass}
                />
              </div>

              {/* 本文 */}
              <div>
                <label className="block text-xs text-zinc-400 mb-1">本文</label>
                <textarea
                  required
                  rows={14}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder="本文を入力"
                  className={`${inputClass} resize-y`}
                />
              </div>

              {error && <p className="text-xs text-red-500">{error}</p>}

              <div className="flex gap-2 justify-end pt-1">
                <button
                  type="button"
                  onClick={() => router.back()}
                  disabled={isPending}
                  className="text-sm px-4 py-2 rounded-lg border border-zinc-200 dark:border-zinc-600 text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors disabled:opacity-50"
                >
                  キャンセル
                </button>
                <button
                  type="submit"
                  disabled={isPending || !toEmail || !subject || !body}
                  className="text-sm px-5 py-2 rounded-lg bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 font-medium hover:bg-zinc-700 dark:hover:bg-zinc-200 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isPending ? "送信中..." : "送信"}
                </button>
              </div>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
