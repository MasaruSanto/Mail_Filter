import type { TokenResponse, UserOut } from "@/lib/types/api";
import { apiFetch } from "./client";

export async function login(body: {
  email: string;
  password: string;
}): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function register(body: {
  email: string;
  password: string;
}): Promise<UserOut> {
  return apiFetch<UserOut>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getMe(token: string): Promise<UserOut> {
  return apiFetch<UserOut>("/api/v1/auth/me", {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getGoogleAuthUrl(token: string): Promise<{ url: string }> {
  return apiFetch<{ url: string }>("/api/v1/auth/google/authorize", {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function changePassword(
  token: string,
  body: { current_password: string; new_password: string }
): Promise<void> {
  return apiFetch<void>("/api/v1/auth/password", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
}

export async function getReplyTemplate(token: string): Promise<{ reply_template: string | null }> {
  return apiFetch<{ reply_template: string | null }>("/api/v1/settings/reply-template", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updateReplyTemplate(token: string, reply_template: string): Promise<void> {
  return apiFetch<void>("/api/v1/settings/reply-template", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ reply_template }),
  });
}

export type ReplyTemplateItem = {
  id: string;
  name: string;
  body: string;
  created_at: string;
};

export async function getReplyTemplates(token: string): Promise<ReplyTemplateItem[]> {
  return apiFetch<ReplyTemplateItem[]>("/api/v1/settings/reply-templates", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function createReplyTemplate(
  token: string,
  body: { name: string; body: string }
): Promise<ReplyTemplateItem> {
  return apiFetch<ReplyTemplateItem>("/api/v1/settings/reply-templates", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function updateReplyTemplateItem(
  token: string,
  id: string,
  body: { name?: string; body?: string }
): Promise<ReplyTemplateItem> {
  return apiFetch<ReplyTemplateItem>(`/api/v1/settings/reply-templates/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function deleteReplyTemplateItem(token: string, id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/settings/reply-templates/${id}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function getPromptSetting(token: string): Promise<{ prompt_instruction: string | null }> {
  return apiFetch<{ prompt_instruction: string | null }>("/api/v1/settings/prompt", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updatePromptSetting(token: string, prompt_instruction: string): Promise<void> {
  return apiFetch<void>("/api/v1/settings/prompt", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt_instruction }),
  });
}

export async function getPipelineSchedule(token: string): Promise<{ interval_minutes: number | null }> {
  return apiFetch<{ interval_minutes: number | null }>("/api/v1/settings/pipeline-schedule", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updatePipelineSchedule(token: string, interval_minutes: number | null): Promise<void> {
  return apiFetch<void>("/api/v1/settings/pipeline-schedule", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ interval_minutes }),
  });
}

export async function getLlmSetting(token: string): Promise<{ provider: string; model: string | null }> {
  return apiFetch<{ provider: string; model: string | null }>("/api/v1/settings/llm", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updateLlmSetting(
  token: string,
  body: { provider: string; api_key?: string; model?: string }
): Promise<void> {
  return apiFetch<void>("/api/v1/settings/llm", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function getSlackSetting(
  token: string
): Promise<{ channel_id: string | null; has_token: boolean }> {
  return apiFetch<{ channel_id: string | null; has_token: boolean }>("/api/v1/settings/slack", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updateSlackSetting(
  token: string,
  body: { bot_token?: string; channel_id?: string }
): Promise<void> {
  return apiFetch<void>("/api/v1/settings/slack", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
}

export async function getWeeklyReportSetting(token: string): Promise<{ enabled: boolean }> {
  return apiFetch<{ enabled: boolean }>("/api/v1/settings/weekly-report", {
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  });
}

export async function updateWeeklyReportSetting(token: string, enabled: boolean): Promise<void> {
  return apiFetch<void>("/api/v1/settings/weekly-report", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ enabled }),
  });
}

export async function sendWeeklyReportNow(token: string): Promise<void> {
  return apiFetch<void>("/api/v1/settings/weekly-report/send-now", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}
