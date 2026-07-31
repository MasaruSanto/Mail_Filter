"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function GoogleCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get("error");
    const hasToken = /(?:^|;\s*)auth_token=/.test(document.cookie);

    if (error) {
      // エラーをダッシュボードに転送して表示させる
      router.replace(`/?google_error=${encodeURIComponent(error)}`);
    } else {
      router.replace(hasToken ? "/" : "/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-900 flex items-center justify-center">
      <p className="text-sm text-zinc-400">認証中...</p>
    </div>
  );
}
