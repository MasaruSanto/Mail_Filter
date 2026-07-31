import { apiFetch } from "./client";
import type { StatsOut } from "../types/api";

// ダッシュボード向けの集計値（総数・未分析数・返信必要数・タグ別件数）を取得する
export const getStats = (token: string): Promise<StatsOut> =>
  apiFetch<StatsOut>("/api/v1/stats", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
