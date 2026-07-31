import { apiFetch } from "./client";
import type { MailDetail, MailListResponse, MailSummary } from "../types/api";

function authHeaders(token: string) {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
}

export type ListMailsParams = {
  q?: string;
  from_email?: string;
  tag?: string;
  needs_reply?: boolean;
  is_analyzed?: boolean;
  has_attachments?: boolean;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
};

// メール一覧を取得する
export const getMails = (token: string, params?: ListMailsParams): Promise<MailListResponse> => {
  const query = new URLSearchParams();
  if (params?.q) query.set("q", params.q);
  if (params?.from_email) query.set("from_email", params.from_email);
  if (params?.tag) query.set("tag", params.tag);
  if (params?.needs_reply != null) query.set("needs_reply", String(params.needs_reply));
  if (params?.is_analyzed != null) query.set("is_analyzed", String(params.is_analyzed));
  if (params?.has_attachments != null) query.set("has_attachments", String(params.has_attachments));
  if (params?.date_from) query.set("date_from", params.date_from);
  if (params?.date_to) query.set("date_to", params.date_to);
  if (params?.limit != null) query.set("limit", String(params.limit));
  if (params?.offset != null) query.set("offset", String(params.offset));
  const qs = query.toString();
  return apiFetch<MailListResponse>(`/api/v1/mails${qs ? `?${qs}` : ""}`, {
    headers: authHeaders(token),
  });
};

// 指定IDのメール詳細をAI分析結果込みで取得する
export const getMail = (token: string, id: string): Promise<MailDetail> =>
  apiFetch<MailDetail>(`/api/v1/mails/${id}`, { headers: authHeaders(token) });

// 指定IDのメールを削除する（MailAssessmentもCASCADE削除される）
export const deleteMail = (token: string, id: string): Promise<void> =>
  apiFetch<void>(`/api/v1/mails/${id}`, { method: "DELETE", headers: authHeaders(token) });

// 指定IDの未分析メールを個別にAI分析する
export const analyzeMail = (token: string, mailId: string): Promise<MailDetail> =>
  apiFetch<MailDetail>(`/api/v1/mails/${mailId}/analyze`, {
    method: "POST",
    headers: authHeaders(token),
  });

// 指定IDのメールに対するAI返信草稿を生成する
export const generateDraft = (
  token: string,
  mailId: string,
): Promise<{ draft: string }> =>
  apiFetch(`/api/v1/mails/${mailId}/draft`, {
    method: "POST",
    headers: authHeaders(token),
  });

// 新規メールを送信する
export const sendMail = (
  token: string,
  data: { to: string; subject: string; body: string }
): Promise<{ message: string; id: string }> =>
  apiFetch("/api/v1/mails/send", {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });

// 指定IDのメールに返信を送信する
export const replyMail = (
  token: string,
  mailId: string,
  data: { to: string; subject: string; body: string; thread_id?: string }
): Promise<{ message: string; id: string }> =>
  apiFetch(`/api/v1/mails/${mailId}/reply`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(data),
  });
