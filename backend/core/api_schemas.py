from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

# --- レスポンススキーマ定義 ---

class AssessmentOut(BaseModel):
  # AIによるメール評価結果
  priority: str
  summarized_body: str
  needs_immediate_reply: bool
  reason: str
  extracted_deadline: Optional[datetime]
  confidence: Optional[float] = None
  ai_response_message: str
  assessed_at: datetime
  replied_at: Optional[datetime] = None

class MailSummaryOut(BaseModel):
  # 一覧表示用（軽量データ）
  id: str
  from_name: Optional[str]
  from_email: Optional[str]
  title: Optional[str]
  day: Optional[date]
  is_analyzed: bool
  has_attachments: bool
  priority: Optional[str]
  needs_immediate_reply: Optional[bool]
  replied_at: Optional[datetime] = None

class Todo(BaseModel):
  id: str
  title: Optional[str]
  body: Optional[str]
  user_id: str
  created_at: datetime
  due_date: Optional[datetime] = None
  status: Optional[str]
  priority: Optional[str] = None

class AttachmentOut(BaseModel):
  id: str
  filename: str
  mime_type: Optional[str] = None
  size: Optional[int] = None

class MailDetailOut(BaseModel):
  # 詳細表示用（本文＋評価結果）
  id: str
  from_name: Optional[str]
  from_email: Optional[str]
  to_name: Optional[str]
  to_email: Optional[str]
  title: Optional[str]
  body: Optional[str]
  has_attachments: bool
  attachments: list[AttachmentOut] = []
  day: Optional[date]
  is_analyzed: bool
  created_at: datetime
  assessment: Optional[AssessmentOut]

class PipelineRunRequest(BaseModel):
  # パイプライン実行リクエスト
  max_results: int = 10
  after_days: Optional[int] = None  # None=無制限、30=直近30日以内

class PipelineRunResponse(BaseModel):
  # パイプライン実行結果
  processed: int
  errors: list[str]

class StatsOut(BaseModel):
  # ダッシュボード用統計
  total: int
  unanalyzed: int
  needs_reply: int

class RegisterRequest(BaseModel):
  email: str
  password: str

class LoginRequest(BaseModel):
  email: str
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"

class UserOut(BaseModel):
  id: str
  email: str
  created_at: datetime
  google_authorized: bool = False

# --- カレンダースキーマ ---
class CalendarEventIn(BaseModel):
  summary: str
  start: datetime
  end: datetime
  location: str = ""
  description: Optional[str] = None

class CalendarEventOut(BaseModel):
  id: str
  summary: str
  description: Optional[str]
  location: Optional[str]
  start: str
  end: str

class TodoCreateRequest(BaseModel):
  title: str
  body: str = ""
  due_date: Optional[datetime] = None
  priority: Optional[str] = None

class TodoUpdateRequest(BaseModel):
  status: str

class TodoEditRequest(BaseModel):
  title: str
  body: str = ""
  due_date: Optional[datetime] = None
  priority: Optional[str] = None

class PasswordChangeRequest(BaseModel):
  current_password: str
  new_password: str

class MailReplyRequest(BaseModel):
  to: str
  subject: str
  body: str
  thread_id: Optional[str] = None

class ReplyTemplateOut(BaseModel):
  reply_template: Optional[str] = None

class ReplyTemplateRequest(BaseModel):
  reply_template: str

class ReplyTemplateItemOut(BaseModel):
  id: str
  name: str
  body: str
  created_at: datetime

class ReplyTemplateItemCreateRequest(BaseModel):
  name: str
  body: str

class ReplyTemplateItemUpdateRequest(BaseModel):
  name: Optional[str] = None
  body: Optional[str] = None

class PromptSettingOut(BaseModel):
  prompt_instruction: Optional[str] = None

class PromptSettingRequest(BaseModel):
  prompt_instruction: str

class PipelineScheduleOut(BaseModel):
  interval_minutes: Optional[int] = None

class PipelineScheduleRequest(BaseModel):
  interval_minutes: Optional[int] = None

class MailListResponse(BaseModel):
  total: int
  mails: list["MailSummaryOut"]

class MailDraftOut(BaseModel):
  draft: str

class ContactOut(BaseModel):
  name: str
  email: str

class LlmSettingOut(BaseModel):
  provider: str
  model: Optional[str] = None

class LlmSettingRequest(BaseModel):
  provider: str
  api_key: Optional[str] = None
  model: Optional[str] = None

class SlackSettingOut(BaseModel):
  channel_id: Optional[str] = None
  has_token: bool = False

class SlackSettingRequest(BaseModel):
  bot_token: Optional[str] = None
  channel_id: Optional[str] = None

class WeeklyReportSettingOut(BaseModel):
  enabled: bool

class WeeklyReportSettingRequest(BaseModel):
  enabled: bool