"use client";

import { useEffect, useState } from "react";
import { getGoogleAuthUrl, getMe } from "@/lib/api/auth";

function getAuthToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)auth_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function GoogleAuthBanner() {
  const [show, setShow] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const googleError = params.get("google_error");
    if (googleError) {
      setErrorMsg(decodeURIComponent(googleError));
      setShow(true);
      // URLからパラメータを消す
      window.history.replaceState({}, "", window.location.pathname);
      return;
    }

    const token = getAuthToken();
    if (!token) return;

    getMe(token)
      .then((user) => { if (!user.google_authorized) setShow(true); })
      .catch(() => {});
  }, []);

  async function handleConnect() {
    setConnecting(true);
    setErrorMsg(null);
    try {
      const token = getAuthToken();
      if (!token) return;
      const { url } = await getGoogleAuthUrl(token);
      window.location.href = url;
    } catch {
      setConnecting(false);
    }
  }

  if (!show) return null;

  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-6 py-3 flex items-start justify-between gap-4">
      <div>
        <p className="text-sm text-amber-800 dark:text-amber-300">
          {errorMsg
            ? "Google連携に失敗しました:"
            : "GmailとGoogleカレンダーへのアクセス許可が必要です。"}
        </p>
        {errorMsg && (
          <p className="text-xs text-amber-700 dark:text-amber-400 mt-1 font-mono break-all">
            {errorMsg}
          </p>
        )}
      </div>
      <button
        onClick={handleConnect}
        disabled={connecting}
        className="shrink-0 text-sm px-4 py-1.5 bg-amber-700 dark:bg-amber-600 text-white rounded-lg hover:bg-amber-800 dark:hover:bg-amber-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {connecting ? "接続中..." : errorMsg ? "再試行" : "Googleと連携する"}
      </button>
    </div>
  );
}
