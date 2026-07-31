// SSR（サーバー側）は INTERNAL_API_URL でコンテナ間通信、ブラウザは NEXT_PUBLIC_API_URL を使用
function getBaseUrl() {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}
const BASE_URL = getBaseUrl();

type ApiError = { detail: string };

// すべてのAPI呼び出しはこの関数を通す
// レスポンスがokでない場合はバックエンドのdetailメッセージをErrorとしてthrowする
export async function apiFetch<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const err: ApiError = await res
      .json()
      .catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail);
  }

  // 204 No Content はボディが存在しないためそのままundefinedを返す
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}
