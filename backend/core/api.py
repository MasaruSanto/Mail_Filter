import logging
import logging.config
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Optional
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session, joinedload

logging.config.dictConfig({
  "version": 1,
  "disable_existing_loggers": False,
  "formatters": {
    "default": {
      "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
      "datefmt": "%Y-%m-%d %H:%M:%S",
    },
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "formatter": "default",
    },
  },
  "root": {
    "level": os.environ.get("LOG_LEVEL", "INFO"),
    "handlers": ["console"],
  },
  # SQLAlchemy の verbose ログを抑制
  "loggers": {
    "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
    "apscheduler": {"level": "INFO", "propagate": True},
  },
})

# --- パス調整（ローカルモジュールをimportできるようにする） ---
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (project_path, os.path.dirname(__file__)):
  if p not in sys.path:
    sys.path.insert(0, p)

# --- DB関連のimport ---
from db.engine import Mail as DBMail
from db.engine import User
from db.engine import MailAssessment as DBAssessment
from db.engine import MailAttachment as DBMailAttachment
from db.engine import TODO as SchemaTODO
from db.engine import ReplyTemplate as DBReplyTemplate
from db.engine import SessionLocal, create_tables
from db.query import get_mail_detail, save_mail_assessment, save_todo, search_mails, get_todo

# --- 認証 ---
from auth import (create_access_token, decode_token, hash_password, verify_password,
                  create_oauth_state_token, decode_oauth_state_token)

# --- Google OAuth ---
from core.google.oauth import exchange_code, get_authorization_url

# --- Google Calendar ---
from core.google.calendar_client import GoogleCalendarClient
from core.google.mail_client import GoogleMailClient
from core.google.people_client import GooglePeopleClient
from core.google.repository import CalendarRepository, ContactsRepository
from core.google.error import GoogleApiError

# --- AIパイプライン ---
from pipeline import MailPipeline
from classifier import MailClassifier
from todo_service import TodoService
from llm_schemas import Mail as LLMMail

# --- 暗号化 ---
from crypto import encrypt, decrypt, decrypt_or_plain

# --- apiモデル ---
from api_schemas import (AssessmentOut, MailSummaryOut, MailListResponse, Todo, MailDetailOut, PipelineRunRequest, PipelineRunResponse, StatsOut,
                         RegisterRequest, LoginRequest, TokenResponse, UserOut, CalendarEventIn, CalendarEventOut, TodoCreateRequest,
                         TodoUpdateRequest, TodoEditRequest, PasswordChangeRequest, MailReplyRequest,
                         ReplyTemplateOut, ReplyTemplateRequest, PromptSettingOut, PromptSettingRequest,
                         PipelineScheduleOut, PipelineScheduleRequest, MailDraftOut, ContactOut,
                         LlmSettingOut, LlmSettingRequest,
                         SlackSettingOut, SlackSettingRequest,
                         WeeklyReportSettingOut, WeeklyReportSettingRequest,
                         AttachmentOut,
                         ReplyTemplateItemOut, ReplyTemplateItemCreateRequest, ReplyTemplateItemUpdateRequest)


_startup_logger = logging.getLogger("api.startup")

# --- FastAPIアプリ初期化 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
  # 必須環境変数の起動時チェック（欠落時は即クラッシュ）
  required = ["ENCRYPTION_KEY", "JWT_SECRET_KEY", "GOOGLE_SECRET_KEY", "GOOGLE_CLIENT_SECRET"]
  missing = [k for k in required if not os.environ.get(k)]
  if missing:
    raise RuntimeError(f"必須環境変数が未設定です: {', '.join(missing)}")

  create_tables()
  import scheduler as sched
  sched.start()
  db = SessionLocal()
  try:
    sched.load_all_schedules(db)
  finally:
    db.close()
  _startup_logger.info("Mail Filter AI 起動完了")
  yield
  sched.shutdown()
  _startup_logger.info("Mail Filter AI シャットダウン完了")

app = FastAPI(title="Mail Filter AI", version="1.0.0", lifespan=lifespan)

http_bearer = HTTPBearer()

# --- CORS設定（CORS_ORIGINS 環境変数でカンマ区切り指定、未設定時はローカル開発用） ---
_cors_origins = [
  o.strip()
  for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
  if o.strip()
]
app.add_middleware(
  CORSMiddleware,
  allow_origins=_cors_origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# --- DB依存性 ---
def get_db():
  """
  リクエストごとにDBセッションを生成し、
  処理終了後に必ずクローズする
  """
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# --- 認証依存性 ---
def get_current_user(
  credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
  db: Session = Depends(get_db),
) -> User:
  try:
    user_id = decode_token(credentials.credentials)
  except JWTError:
    raise HTTPException(status_code=401, detail="認証トークンが無効です")

  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    raise HTTPException(status_code=401, detail="ユーザーが見つかりません")
  return user

# --- ヘルパー関数 ---

def _to_mail_summary(m: DBMail) -> MailSummaryOut:
  """
  DBモデル → 一覧用レスポンスに変換
  assessmentが無い場合はNoneを返す
  """
  a = m.assessment
  return MailSummaryOut(
    id=str(m.id),
    from_name=m.from_name,
    from_email=m.from_email,
    title=m.title,
    day=m.day,
    is_analyzed=a is not None,
    has_attachments=m.has_attachments,
    priority=a.priority if a else None,
    needs_immediate_reply=a.needs_immediate_reply if a else None,
    replied_at=a.replied_at if a else None,
  )

def _to_mail_detail(m: DBMail) -> MailDetailOut:
  """
  DBモデル → 詳細レスポンスに変換
  """
  a = m.assessment
  return MailDetailOut(
    id=str(m.id),
    from_name=m.from_name,
    from_email=m.from_email,
    to_name=m.to_name,
    to_email=m.to_email,
    title=m.title,
    body=m.body,
    has_attachments=m.has_attachments,
    attachments=[
      AttachmentOut(id=str(att.id), filename=att.filename, mime_type=att.mime_type, size=att.size)
      for att in m.attachments
    ],
    day=m.day,
    is_analyzed=a is not None,
    created_at=m.created_at,
    assessment=AssessmentOut(
      priority=a.priority,
      summarized_body=a.summarized_body,
      needs_immediate_reply=a.needs_immediate_reply,
      reason=a.reason,
      extracted_deadline=a.extracted_deadline,
      confidence=getattr(a, "confidence", None),
      ai_response_message=a.ai_response_message,
      assessed_at=a.assessed_at,
      replied_at=a.replied_at,
    ) if a else None,
  )

# --- エンドポイント ---

@app.get("/health")
async def health():
  # ヘルスチェック
  return {"status": "ok"}


# --- 認証エンドポイント ---

@app.post("/api/v1/auth/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
  if db.query(User).filter(User.email == body.email).first():
    raise HTTPException(status_code=400, detail="このメールアドレスは既に登録されています")

  if len(body.password) < 8:
    raise HTTPException(status_code=400, detail="パスワードは8文字以上で設定してください")

  user = User(
    id=str(uuid.uuid4()),
    email=body.email,
    hashed_password=hash_password(body.password),
  )
  db.add(user)
  db.commit()
  db.refresh(user)
  return UserOut(id=str(user.id), email=user.email, created_at=user.created_at)


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_db)):
  user = db.query(User).filter(User.email == body.email).first()
  if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
    raise HTTPException(status_code=401, detail="メールアドレスまたはパスワードが違います")

  token = create_access_token(str(user.id))
  return TokenResponse(access_token=token)


@app.get("/api/v1/auth/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
  return UserOut(
    id=str(current_user.id),
    email=current_user.email,
    created_at=current_user.created_at,
    google_authorized=current_user.google_refresh_token is not None,
  )


@app.get("/api/v1/auth/google/authorize")
async def google_authorize(current_user: User = Depends(get_current_user)):
  # stateには生のuser_idではなく短命の署名付きトークンを使う（CSRF対策）
  url = get_authorization_url(create_oauth_state_token(str(current_user.id)))
  return {"url": url}


@app.get("/api/v1/auth/google/callback")
async def google_callback(code: str, state: str, db: Session = Depends(get_db)):
  try:
    user_id = decode_oauth_state_token(state)
  except JWTError:
    return RedirectResponse("http://localhost:3000/google-callback?error=invalid_state", status_code=302)

  _frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000")

  user = db.query(User).filter(User.id == user_id).first()
  if not user:
    return RedirectResponse(f"{_frontend}/google-callback?error=1", status_code=302)

  try:
    refresh_token, scopes = exchange_code(code, state)
    if not refresh_token:
      logging.getLogger("api.oauth").warning("Google OAuth: refresh_token が取得できませんでした")
      return RedirectResponse(f"{_frontend}/google-callback?error=no_refresh_token", status_code=302)
    user.google_refresh_token = encrypt(refresh_token)
    user.google_token_scope = scopes
    db.commit()
  except Exception as e:
    logging.getLogger("api.oauth").error("Google OAuth callback エラー: %s: %s", type(e).__name__, e)
    return RedirectResponse(f"{_frontend}/google-callback?error=oauth_failed", status_code=302)

  return RedirectResponse(f"{_frontend}/google-callback", status_code=302)

@app.put("/api/v1/auth/password", status_code=200)
async def change_password(
  body: PasswordChangeRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  if not current_user.hashed_password or not verify_password(body.current_password, current_user.hashed_password):
    raise HTTPException(status_code=400, detail="現在のパスワードが正しくありません")
  if len(body.new_password) < 8:
    raise HTTPException(status_code=400, detail="パスワードは8文字以上で設定してください")
  current_user.hashed_password = hash_password(body.new_password)
  db.commit()
  return {"message": "パスワードを変更しました"}


@app.get("/api/v1/settings/reply-template", response_model=ReplyTemplateOut)
async def get_reply_template(current_user: User = Depends(get_current_user)):
  return ReplyTemplateOut(reply_template=current_user.reply_template)

@app.put("/api/v1/settings/reply-template", response_model=ReplyTemplateOut)
async def update_reply_template(
  body: ReplyTemplateRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  current_user.reply_template = body.reply_template
  db.commit()
  return ReplyTemplateOut(reply_template=current_user.reply_template)


@app.get("/api/v1/settings/reply-templates", response_model=list[ReplyTemplateItemOut])
async def list_reply_templates(
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  templates = (
    db.query(DBReplyTemplate)
    .filter(DBReplyTemplate.user_id == current_user.id)
    .order_by(DBReplyTemplate.created_at)
    .all()
  )
  # 旧仕様（単一テンプレート）からの一回限りの移行
  if not templates and current_user.reply_template:
    legacy = DBReplyTemplate(
      user_id=current_user.id,
      name="デフォルト",
      body=current_user.reply_template,
    )
    db.add(legacy)
    db.commit()
    db.refresh(legacy)
    templates = [legacy]
  return [
    ReplyTemplateItemOut(id=str(t.id), name=t.name, body=t.body, created_at=t.created_at)
    for t in templates
  ]

@app.post("/api/v1/settings/reply-templates", response_model=ReplyTemplateItemOut, status_code=201)
async def create_reply_template(
  body: ReplyTemplateItemCreateRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  template = DBReplyTemplate(user_id=current_user.id, name=body.name, body=body.body)
  db.add(template)
  db.commit()
  db.refresh(template)
  return ReplyTemplateItemOut(id=str(template.id), name=template.name, body=template.body, created_at=template.created_at)

@app.put("/api/v1/settings/reply-templates/{template_id}", response_model=ReplyTemplateItemOut)
async def update_reply_template_item(
  template_id: str,
  body: ReplyTemplateItemUpdateRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  template = db.query(DBReplyTemplate).filter(
    DBReplyTemplate.id == template_id,
    DBReplyTemplate.user_id == current_user.id,
  ).first()
  if not template:
    raise HTTPException(status_code=404, detail="テンプレートが見つかりません")
  if body.name is not None:
    template.name = body.name
  if body.body is not None:
    template.body = body.body
  db.commit()
  return ReplyTemplateItemOut(id=str(template.id), name=template.name, body=template.body, created_at=template.created_at)

@app.delete("/api/v1/settings/reply-templates/{template_id}", status_code=204)
async def delete_reply_template_item(
  template_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  template = db.query(DBReplyTemplate).filter(
    DBReplyTemplate.id == template_id,
    DBReplyTemplate.user_id == current_user.id,
  ).first()
  if not template:
    raise HTTPException(status_code=404, detail="テンプレートが見つかりません")
  db.delete(template)
  db.commit()


@app.get("/api/v1/settings/pipeline-schedule", response_model=PipelineScheduleOut)
async def get_pipeline_schedule(current_user: User = Depends(get_current_user)):
  minutes_str = current_user.pipeline_schedule_minutes
  minutes = int(minutes_str) if minutes_str and minutes_str.isdigit() else None
  return PipelineScheduleOut(interval_minutes=minutes)

@app.put("/api/v1/settings/pipeline-schedule", response_model=PipelineScheduleOut)
async def update_pipeline_schedule(
  body: PipelineScheduleRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  import scheduler as sched
  current_user.pipeline_schedule_minutes = str(body.interval_minutes) if body.interval_minutes else None
  db.commit()
  if body.interval_minutes:
    sched.schedule_user(str(current_user.id), body.interval_minutes)
  else:
    sched.unschedule_user(str(current_user.id))
  minutes = body.interval_minutes
  return PipelineScheduleOut(interval_minutes=minutes)


@app.get("/api/v1/settings/prompt", response_model=PromptSettingOut)
async def get_prompt_setting(current_user: User = Depends(get_current_user)):
  return PromptSettingOut(prompt_instruction=current_user.prompt_instruction)

@app.put("/api/v1/settings/prompt", response_model=PromptSettingOut)
async def update_prompt_setting(
  body: PromptSettingRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  current_user.prompt_instruction = body.prompt_instruction
  db.commit()
  return PromptSettingOut(prompt_instruction=current_user.prompt_instruction)


@app.get("/api/v1/settings/llm", response_model=LlmSettingOut)
async def get_llm_setting(current_user: User = Depends(get_current_user)):
  return LlmSettingOut(
    provider=current_user.llm_provider or "local",
    model=current_user.openai_model,
  )

@app.put("/api/v1/settings/llm", response_model=LlmSettingOut)
async def update_llm_setting(
  body: LlmSettingRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  if body.provider not in ("local", "openai"):
    raise HTTPException(status_code=422, detail="providerは 'local' または 'openai' を指定してください")
  current_user.llm_provider = body.provider
  if body.api_key is not None:
    current_user.openai_api_key = encrypt(body.api_key) if body.api_key else None
  if body.model is not None:
    current_user.openai_model = body.model or None
  db.commit()
  return LlmSettingOut(provider=current_user.llm_provider, model=current_user.openai_model)


@app.get("/api/v1/settings/slack", response_model=SlackSettingOut)
async def get_slack_setting(current_user: User = Depends(get_current_user)):
  return SlackSettingOut(
    channel_id=current_user.slack_channel_id,
    has_token=bool(current_user.slack_bot_token),
  )

@app.put("/api/v1/settings/slack", response_model=SlackSettingOut)
async def update_slack_setting(
  body: SlackSettingRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  if body.bot_token is not None:
    current_user.slack_bot_token = encrypt(body.bot_token) if body.bot_token else None
  if body.channel_id is not None:
    current_user.slack_channel_id = body.channel_id or None
  db.commit()
  return SlackSettingOut(
    channel_id=current_user.slack_channel_id,
    has_token=bool(current_user.slack_bot_token),
  )


@app.get("/api/v1/settings/weekly-report", response_model=WeeklyReportSettingOut)
async def get_weekly_report_setting(current_user: User = Depends(get_current_user)):
  return WeeklyReportSettingOut(enabled=bool(current_user.weekly_report_enabled))

@app.put("/api/v1/settings/weekly-report", response_model=WeeklyReportSettingOut)
async def update_weekly_report_setting(
  body: WeeklyReportSettingRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  import scheduler as sched
  current_user.weekly_report_enabled = body.enabled
  db.commit()
  if body.enabled:
    sched.schedule_weekly_report(str(current_user.id))
  else:
    sched.unschedule_weekly_report(str(current_user.id))
  return WeeklyReportSettingOut(enabled=current_user.weekly_report_enabled)

@app.post("/api/v1/settings/weekly-report/send-now", status_code=204)
async def send_weekly_report_now(
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  from weekly_report import send_weekly_report as _send_weekly_report
  if not current_user.google_refresh_token:
    raise HTTPException(status_code=400, detail="Google連携が必要です")
  try:
    _send_weekly_report(db, current_user)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"送信失敗: {e}")


@app.get("/api/v1/mails", response_model=MailListResponse)
async def list_mails(
  q: Optional[str] = None,
  from_email: Optional[str] = None,
  tag: Optional[str] = None,
  needs_reply: Optional[bool] = None,
  is_analyzed: Optional[bool] = None,
  has_attachments: Optional[bool] = None,
  date_from: Optional[date] = None,
  date_to: Optional[date] = None,
  limit: int = 50,
  offset: int = 0,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mails, total = search_mails(
    db,
    user_id=current_user.id,
    q=q,
    from_email=from_email,
    tag=tag,
    needs_reply=needs_reply,
    is_analyzed=is_analyzed,
    has_attachments=has_attachments,
    date_from=date_from,
    date_to=date_to,
    limit=min(limit, 200),
    offset=offset,
  )
  return MailListResponse(total=total, mails=[_to_mail_summary(m) for m in mails])

@app.post("/api/v1/mails/send", status_code=200)
async def send_mail(
  body: MailReplyRequest,
  current_user: User = Depends(get_current_user),
):
  if not current_user.google_refresh_token:
    raise HTTPException(status_code=403, detail="Googleと連携してください")
  try:
    from core.google.repository import MailRepository
    repo = MailRepository(GoogleMailClient(refresh_token=decrypt_or_plain(current_user.google_refresh_token)))
    result = repo.send_reply(to=body.to, subject=body.subject, body=body.body)
    return {"message": "送信しました", "id": result.get("id")}
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/mails/{mail_id}", response_model=MailDetailOut)
async def get_mail(
  mail_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mail = get_mail_detail(db, mail_id, user_id=current_user.id)
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")

  return _to_mail_detail(mail)

@app.get("/api/v1/mails/{mail_id}/attachments/{attachment_id}/download")
async def download_attachment(
  mail_id: str,
  attachment_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mail = get_mail_detail(db, mail_id, user_id=current_user.id)
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")

  attachment = db.query(DBMailAttachment).filter(
    DBMailAttachment.id == attachment_id,
    DBMailAttachment.mail_id == mail_id,
  ).first()
  if not attachment:
    raise HTTPException(status_code=404, detail="添付ファイルが見つかりません")

  if not current_user.google_refresh_token:
    raise HTTPException(status_code=403, detail="Googleと連携してください")

  from core.google.repository import MailRepository
  from urllib.parse import quote
  repo = MailRepository(GoogleMailClient(refresh_token=decrypt_or_plain(current_user.google_refresh_token)))
  try:
    content = repo.fetch_attachment(mail_id, attachment.attachment_id)
  except Exception as e:
    raise HTTPException(status_code=502, detail=f"添付ファイルの取得に失敗しました: {e}")

  filename_encoded = quote(attachment.filename)
  return Response(
    content=content,
    media_type=attachment.mime_type or "application/octet-stream",
    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename_encoded}"},
  )

@app.post("/api/v1/mails/{mail_id}/reply", status_code=200)
async def reply_mail(
  mail_id: str,
  body: MailReplyRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  if not current_user.google_refresh_token:
    raise HTTPException(status_code=403, detail="Googleと連携してください")

  mail = get_mail_detail(db, mail_id, user_id=current_user.id)
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")

  try:
    from core.google.repository import MailRepository
    repo = MailRepository(GoogleMailClient(refresh_token=decrypt_or_plain(current_user.google_refresh_token)))
    result = repo.send_reply(
      to=body.to,
      subject=body.subject,
      body=body.body,
      thread_id=body.thread_id,
    )
    if mail.assessment:
      mail.assessment.replied_at = datetime.now()
      db.commit()
    return {"message": "送信しました", "id": result.get("id")}
  except HTTPException:
    raise
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/mails/{mail_id}/draft", response_model=MailDraftOut)
async def generate_mail_draft(
  mail_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mail = get_mail_detail(db, mail_id, user_id=current_user.id)
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")
  if not mail.body or not mail.body.strip():
    raise HTTPException(status_code=422, detail="本文が空のため生成できません")

  try:
    from draft_generator import MailDraftGenerator
    generator = MailDraftGenerator(
      provider=current_user.llm_provider,
      api_key=decrypt(current_user.openai_api_key) if current_user.openai_api_key else None,
      llm_model=current_user.openai_model,
    )
    draft = generator.generate(
      from_name=mail.from_name or "",
      from_email=mail.from_email or "",
      title=mail.title or "",
      body=mail.body,
    )
    return MailDraftOut(draft=draft)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"AI生成に失敗しました: {str(e)}")


@app.post("/api/v1/mails/{mail_id}/analyze", response_model=MailDetailOut)
async def analyze_mail(
  mail_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mail = get_mail_detail(db, mail_id, user_id=current_user.id)
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")
  if mail.assessment is not None:
    raise HTTPException(status_code=409, detail="既に分析済みです")
  if not mail.body or not mail.body.strip():
    raise HTTPException(status_code=422, detail="本文が空のため分析できません")

  llm_mail = LLMMail(
    id=str(mail.id),
    from_name=mail.from_name,
    from_email=mail.from_email,
    to_name=mail.to_name,
    to_email=mail.to_email,
    title=mail.title,
    body=mail.body,
    has_attachments=mail.has_attachments,
    day=mail.day,
  )

  try:
    classifier = MailClassifier(
      extra_instruction=current_user.prompt_instruction or "",
      provider=current_user.llm_provider or "local",
      api_key=decrypt(current_user.openai_api_key) if current_user.openai_api_key else None,
      llm_model=current_user.openai_model,
    )
    analyzed = classifier.classify(llm_mail)

    if analyzed.mail_ai_analysis.should_create_todo:
      todo = TodoService(
        provider=current_user.llm_provider or "local",
        api_key=decrypt(current_user.openai_api_key) if current_user.openai_api_key else None,
        llm_model=current_user.openai_model,
      ).create(analyzed_mail=analyzed, user_id=str(current_user.id))
      save_todo(db, str(current_user.id), todo, analyzed.mail_ai_analysis.extracted_deadline)

    save_mail_assessment(db, str(mail.id), analyzed.mail_ai_analysis)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"AI分析に失敗しました: {e}")

  updated = get_mail_detail(db, mail_id, user_id=current_user.id)
  return _to_mail_detail(updated)


@app.delete("/api/v1/mails/{mail_id}", status_code=204)
async def delete_mail(
  mail_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  mail = db.query(DBMail).filter(
    DBMail.id == mail_id, DBMail.user_id == current_user.id
  ).first()
  if not mail:
    raise HTTPException(status_code=404, detail="メールが見つかりません")

  db.delete(mail)
  db.commit()

@app.post("/api/v1/pipeline/run", response_model=PipelineRunResponse)
async def run_pipeline(
  body: PipelineRunRequest,
  current_user: User = Depends(get_current_user),
):
  if not current_user.google_refresh_token:
    raise HTTPException(status_code=403, detail="Googleと連携してください")

  errors: list[str] = []
  processed = 0

  try:
    pipeline = MailPipeline(
      user_id=str(current_user.id),
      refresh_token=decrypt_or_plain(current_user.google_refresh_token),
      max_results=body.max_results,
      after_days=body.after_days,
      extra_instruction=current_user.prompt_instruction or "",
      llm_provider="local",
      llm_api_key=decrypt(current_user.openai_api_key) if current_user.openai_api_key else None,
      llm_model=current_user.openai_model,
    )
    processed, mail_errors = pipeline.run()
    errors.extend(mail_errors)
  except Exception as e:
    errors.append(str(e))

  return PipelineRunResponse(processed=processed, errors=errors)

@app.get("/api/v1/stats", response_model=StatsOut)
async def get_stats(
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  total = db.query(DBMail).filter(DBMail.user_id == current_user.id).count()

  unanalyzed = db.query(DBMail).filter(
    DBMail.user_id == current_user.id,
    DBMail.is_analyzed == False,
  ).count()

  needs_reply = (
    db.query(DBAssessment)
    .join(DBMail, DBAssessment.mail_id == DBMail.id)
    .filter(DBMail.user_id == current_user.id, DBAssessment.needs_immediate_reply == True)
    .count()
  )

  return StatsOut(
    total=total,
    unanalyzed=unanalyzed,
    needs_reply=needs_reply,
  )

def _to_calendar_event_out(ev: dict) -> CalendarEventOut:
  start = ev.get("start", {})
  end = ev.get("end", {})
  return CalendarEventOut(
    id=ev["id"],
    summary=ev.get("summary", ""),
    description=ev.get("description"),
    location=ev.get("location"),
    start=start.get("dateTime") or start.get("date", ""),
    end=end.get("dateTime") or end.get("date", ""),
  )

def _calendar_repo(user: User) -> CalendarRepository:
  if not user.google_refresh_token:
    raise HTTPException(status_code=403, detail="Googleと連携してください")
  return CalendarRepository(GoogleCalendarClient(refresh_token=decrypt_or_plain(user.google_refresh_token)))


# --- カレンダーエンドポイント ---

@app.get("/api/v1/calendar/events", response_model=list[CalendarEventOut])
async def get_calendar_events(
  current_user: User = Depends(get_current_user),
):
  try:
    repo = _calendar_repo(current_user)
    from datetime import timezone
    now = datetime.now(timezone.utc)
    events = repo.fetch_events(max_results=50, time_min=now)
    return [_to_calendar_event_out(ev) for ev in events]
  except HTTPException:
    raise
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/calendar/events", response_model=CalendarEventOut, status_code=201)
async def create_calendar_event(
  body: CalendarEventIn,
  current_user: User = Depends(get_current_user),
):
  try:
    repo = _calendar_repo(current_user)
    ev = repo.create_event(
      summary=body.summary,
      location=body.location,
      start=body.start,
      end=body.end,
      description=body.description,
    )
    return _to_calendar_event_out(ev)
  except HTTPException:
    raise
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/calendar/events/{event_id}", response_model=CalendarEventOut)
async def update_calendar_event(
  event_id: str,
  body: CalendarEventIn,
  current_user: User = Depends(get_current_user),
):
  try:
    repo = _calendar_repo(current_user)
    ev = repo.update_event(
      event_id=event_id,
      summary=body.summary,
      location=body.location,
      start=body.start,
      end=body.end,
      description=body.description,
    )
    return _to_calendar_event_out(ev)
  except HTTPException:
    raise
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/calendar/events/{event_id}", status_code=204)
async def delete_calendar_event(
  event_id: str,
  current_user: User = Depends(get_current_user),
):
  try:
    repo = _calendar_repo(current_user)
    repo.delete_event(event_id)
  except HTTPException:
    raise
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/todos", response_model=Todo, status_code=201)
async def create_todo(
  body: TodoCreateRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  from db.engine import TodoStatus as DBTodoStatus
  from db.engine import TodoPriority as DBTodoPriority
  todo = SchemaTODO(
    id=str(uuid.uuid4()),
    title=body.title,
    body=body.body,
    due_date=body.due_date,
    user_id=current_user.id,
    status=DBTodoStatus.NOT_STARTED,
  )
  if body.priority:
    try:
      todo.priority = DBTodoPriority(body.priority)
    except ValueError:
      raise HTTPException(status_code=400, detail=f"無効な優先度: {body.priority}")
  db.add(todo)
  db.commit()
  db.refresh(todo)
  return todo

@app.patch("/api/v1/todos/{todo_id}", response_model=Todo)
async def update_todo_status(
  todo_id: str,
  body: TodoUpdateRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  from db.engine import TodoStatus as DBTodoStatus
  todo = (
    db.query(SchemaTODO)
    .filter(SchemaTODO.id == todo_id, SchemaTODO.user_id == current_user.id)
    .first()
  )
  if not todo:
    raise HTTPException(status_code=404, detail="TODOが見つかりません")
  try:
    todo.status = DBTodoStatus(body.status)
  except ValueError:
    raise HTTPException(status_code=400, detail=f"無効なステータス: {body.status}")
  db.commit()
  db.refresh(todo)
  return todo

@app.put("/api/v1/todos/{todo_id}", response_model=Todo)
async def update_todo(
  todo_id: str,
  body: TodoEditRequest,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  todo = (
    db.query(SchemaTODO)
    .filter(SchemaTODO.id == todo_id, SchemaTODO.user_id == current_user.id)
    .first()
  )
  if not todo:
    raise HTTPException(status_code=404, detail="TODOが見つかりません")
  todo.title = body.title
  todo.body = body.body
  todo.due_date = body.due_date
  if body.priority:
    from db.engine import TodoPriority as DBTodoPriority
    try:
      todo.priority = DBTodoPriority(body.priority)
    except ValueError:
      raise HTTPException(status_code=400, detail=f"無効な優先度: {body.priority}")
  db.commit()
  db.refresh(todo)
  return todo

@app.delete("/api/v1/todos/{todo_id}", status_code=204)
async def delete_todo(
  todo_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  todo = (
    db.query(SchemaTODO)
    .filter(SchemaTODO.id == todo_id, SchemaTODO.user_id == current_user.id)
    .first()
  )
  if not todo:
    raise HTTPException(status_code=404, detail="TODOが見つかりません")

  db.delete(todo)
  db.commit()

@app.get("/api/v1/todos", response_model=list[Todo])
async def get_todo_list(
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  return (
    db.query(SchemaTODO)
    .filter(SchemaTODO.user_id == current_user.id)
    .order_by(SchemaTODO.created_at.desc())
    .all()
  )

@app.get("/api/v1/todos/{todo_id}", response_model=Todo)
async def get_todo_detail(
  todo_id: str,
  current_user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
):
  todo = get_todo(db, todo_id, user_id=current_user.id)
  if not todo:
    raise HTTPException(status_code=404, detail="TODOが見つかりません")
  return todo

# --- 音声文字起こし ---

@app.get("/api/v1/contacts", response_model=list[ContactOut])
def get_contacts(
  current_user: User = Depends(get_current_user),
):
  if not current_user.google_refresh_token:
    raise HTTPException(status_code=400, detail="Google連携が必要です")
  try:
    client = GooglePeopleClient(refresh_token=decrypt_or_plain(current_user.google_refresh_token))
    repo = ContactsRepository(client=client)
    return repo.fetch_contacts()
  except GoogleApiError as e:
    raise HTTPException(status_code=e.status_code, detail=str(e))
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"連絡先の取得に失敗しました: {e}")


_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB

@app.post("/api/v1/speech/transcribe")
async def transcribe_speech(
  audio: UploadFile = File(...),
  current_user: User = Depends(get_current_user),
):
  import tempfile
  from pathlib import Path
  suffix = Path(audio.filename or "recording.webm").suffix or ".webm"
  content = await audio.read(_MAX_AUDIO_BYTES + 1)
  if len(content) > _MAX_AUDIO_BYTES:
    raise HTTPException(status_code=413, detail="音声ファイルは25MB以下にしてください")
  with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
    tmp.write(content)
    tmp_path = tmp.name
  try:
    from speech.transcriber import transcribe_file
    text = transcribe_file(tmp_path)
    return {"text": text}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"文字起こしに失敗しました: {e}")
  finally:
    os.unlink(tmp_path)


# --- アプリ起動 ---
if __name__ == "__main__":
  uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")