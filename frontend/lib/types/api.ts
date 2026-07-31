export type Priority =
  | "迷惑メール"
  | "業務メール"
  | "営業メール"
  | "個人メール"
  | "緊急メール"
  | "返信必要"
  | "対応待ち"
  | "社内メール";

export type AssessmentOut = {
  priority: Priority;
  summarized_body: string;
  needs_immediate_reply: boolean;
  reason: string;
  extracted_deadline: string | null;
  confidence: number;
  ai_response_message: string;
  assessed_at: string;
  replied_at: string | null;
};

export type MailSummary = {
  id: string;
  from_name: string | null;
  from_email: string | null;
  title: string | null;
  day: string | null;
  is_analyzed: boolean;
  has_attachments: boolean;
  priority: Priority | null;
  needs_immediate_reply: boolean | null;
  replied_at: string | null;
};

export type Attachment = {
  id: string;
  filename: string;
  mime_type: string | null;
  size: number | null;
};

export type MailDetail = MailSummary & {
  to_name: string | null;
  to_email: string | null;
  body: string | null;
  attachments: Attachment[];
  created_at: string;
  assessment: AssessmentOut | null;
};

export type MailListResponse = {
  total: number;
  mails: MailSummary[];
};

export type StatsOut = {
  total: number;
  unanalyzed: number;
  needs_reply: number;
};

export type PipelineRunResponse = {
  processed: number;
  errors: string[];
};

export type TodoStatus = "未対応" | "処理中" | "処理済み" | "完了";
export type TodoPriority = "高" | "中" | "低";

export type Todo = {
  id: string;
  title: string | null;
  body: string | null;
  user_id: string;
  created_at: string;
  due_date: string | null;
  status: TodoStatus | null;
  priority: TodoPriority | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UserOut = {
  id: string;
  email: string;
  created_at: string;
  google_authorized: boolean;
};

export type CalendarEvent = {
  id: string;
  summary: string;
  description: string | null;
  location: string | null;
  start: string; // ISO datetime
  end: string;   // ISO datetime
};
