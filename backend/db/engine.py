import uuid
import os
import sys
import uuid

# projectディレクトリの絶対パスを取得して追加
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_path not in sys.path:
  sys.path.insert(0, project_path)

from datetime import datetime
from sqlalchemy import (Boolean, Column, DateTime, Enum, ForeignKey,
                        Integer, Text, create_engine, String, event, text)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from core.enums import TagType, TodoStatus, TodoPriority

_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'priority.db'))
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
  DATABASE_URL,
  echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
  connect_args={
    "check_same_thread": False,
    "timeout": 30,  # ロック競合時に最大30秒待機してからエラー
  },
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
  cursor = dbapi_conn.cursor()
  cursor.execute("PRAGMA journal_mode=WAL")   # 同時読み書きを許容
  cursor.execute("PRAGMA synchronous=NORMAL") # WAL時の最適な設定
  cursor.execute("PRAGMA foreign_keys=ON")    # 外部キー制約を有効化
  cursor.close()

SessionLocal = sessionmaker(
  bind=engine,
  autoflush=False,
  autocommit=False,
)

Base  = declarative_base()

class User(Base):
  __tablename__ = "user"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  email = Column(String(255), nullable=False, unique=True, index=True)
  hashed_password = Column(String(255), nullable=True)
  google_sub = Column(String(255), nullable=True, unique=True, index=True)
  google_refresh_token = Column(
    String(512),
    nullable=True,
    comment="Gmail API 用 refresh token"
  )
  google_token_scope = Column(
    Text,
    nullable=True,
    comment="許可されたOAuthスコープ"
)
  reply_template = Column(Text, nullable=True, comment="返信テンプレート")
  prompt_instruction = Column(Text, nullable=True, comment="LLM分類への追加指示")
  pipeline_schedule_minutes = Column(String(10), nullable=True, default="30", comment="パイプライン自動実行間隔（分）、nullで無効")
  llm_provider = Column(String(20), nullable=False, default="local", comment="LLMプロバイダー: local | openai")
  openai_api_key = Column(Text, nullable=True, comment="OpenAI APIキー")
  openai_model = Column(String(50), nullable=True, default="gpt-4o-mini", comment="OpenAI モデル名")
  slack_bot_token = Column(Text, nullable=True, comment="Slack Bot Token（暗号化済み）")
  slack_channel_id = Column(String(100), nullable=True, comment="Slack 通知先チャンネルID")
  weekly_report_enabled = Column(Boolean, nullable=False, default=False, comment="週次メールサマリーレポートの自動送信有無")
  created_at = Column(DateTime, default=datetime.now, nullable=False)
  updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

class ReplyTemplate(Base):
  __tablename__ = "reply_templates"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  user_id = Column(
    String(36),
    ForeignKey("user.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )
  name = Column(String(100), nullable=False, comment="テンプレート名（クライアント名・用途など）")
  body = Column(Text, nullable=False)
  created_at = Column(DateTime, default=datetime.now, nullable=False)
  updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
  user = relationship("User", backref="reply_templates")

class Mail(Base):
  __tablename__ = "mails"

  id = Column(
    String(36),
    primary_key=True,
    default=lambda: str(uuid.uuid4()),
  )

  # 送信者情報
  from_name = Column(Text, nullable=True, comment="送り人名")
  from_email = Column(Text, nullable=True, comment="送信元メールアドレス")

  # 宛先情報
  to_name = Column(Text, nullable=True, comment="宛先名")
  to_email = Column(Text, nullable=True, comment="宛先メールアドレス")

  # メール本文
  title = Column(Text, nullable=True, comment="メールタイトル")
  body = Column(Text, nullable=True, comment="メール本文")

  # フラグ・日付
  has_attachments = Column(
    Boolean,
    nullable=False,
    default=False,
    comment="添付ファイル有無"
  )
  day = Column(DateTime, nullable=True, comment="送信日")
  is_analyzed = Column(
    Boolean,
    nullable=False,
    default=False,
    comment="AI解析済みフラグ（true: 解析済み / false: 未解析）"
  )
  created_at = Column(
    DateTime,
    nullable=False,
    default=datetime.now,
  )
  user_id = Column(
    String(36),
    ForeignKey("user.id", ondelete="CASCADE"),
    nullable=True,
    index=True,
  )
  user = relationship("User", backref="mails")
  assessment = relationship(
    "MailAssessment",
    back_populates="mail",
    uselist=False,
    cascade="all, delete-orphan",
  )
  attachments = relationship(
    "MailAttachment",
    back_populates="mail",
    cascade="all, delete-orphan",
  )

class MailAttachment(Base):
  __tablename__ = "mail_attachments"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  mail_id = Column(
    String(36),
    ForeignKey("mails.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
  )
  attachment_id = Column(Text, nullable=False, comment="Gmail API の添付ファイルID")
  filename = Column(Text, nullable=False)
  mime_type = Column(String(255), nullable=True)
  size = Column(Integer, nullable=True, comment="ファイルサイズ（バイト）")
  mail = relationship("Mail", back_populates="attachments")

class MailAssessment(Base):
  __tablename__ = "mail_assessments"
  "評価対象となるメールのID"
  mail_id = Column(
    String(36),
    ForeignKey("mails.id", ondelete="CASCADE"),
    primary_key=True,
  )
  mail = relationship("Mail", back_populates="assessment")
  "AIが要点を抽出したメール本文の要約"
  summarized_body = Column(Text, nullable=False)
  "AIが判定したメールの優先度"
  priority = Column(
    Enum(TagType, name="priority"),
    nullable=False,
  )
  "即時返信が必要かどうか"
  needs_immediate_reply = Column(Boolean, nullable=False)
  "優先度や判定理由"
  reason = Column(Text, nullable=False)
  "本文から抽出された期限（存在しない場合はNone）"
  extracted_deadline = Column(DateTime, nullable=True)
  "評価日時（ユーザーが返信したかどうかに関わらず、AIが評価を行った日時）"
  assessed_at = Column(
    DateTime,
    nullable=False,
    default=datetime.now,
  )
  "ユーザーが返信した場合の返信日時（未返信はNone）"
  replied_at = Column(
    DateTime,
    nullable=True,
    comment="返信送信日時（未返信はNone）"
  )
  "AIの返信メッセージ（ユーザーが返信した場合のみ保存）"
  ai_response_message = Column(
    Text,
    nullable=False,
    comment="元メールに対してAIが生成した返信用メッセージ（送信前／送信内容の元データ）"
  )

class TODO(Base):
  __tablename__ = "todo"

  id = Column(
    String(36),
    primary_key=True,
    default=lambda: str(uuid.uuid4()),
  )

  title = Column(Text, nullable=False)
  body = Column(Text, nullable=False)

  created_at = Column(
    DateTime,
    nullable=False,
    default=datetime.now,
  )

  due_date = Column(DateTime, nullable=True, comment="終了日")

  user_id = Column(
    String(36),
    ForeignKey("user.id", ondelete="CASCADE"),
    primary_key=True,
  )

  status = Column(
    Enum(TodoStatus),
    nullable=False,
    default=TodoStatus.NOT_STARTED
  )

  priority = Column(
    Enum(TodoPriority),
    nullable=False,
    default=TodoPriority.MEDIUM
  )

  user = relationship("User", backref="todos")
 


def create_tables():
  Base.metadata.create_all(engine)
  _migrate()

def _migrate():
  """既存DBへのカラム追加（冪等）"""
  migrations = [
    "ALTER TABLE user ADD COLUMN prompt_instruction TEXT",
    "ALTER TABLE user ADD COLUMN pipeline_schedule_minutes VARCHAR(10) DEFAULT '30'",
    "ALTER TABLE user ADD COLUMN llm_provider VARCHAR(20) DEFAULT 'local'",
    "ALTER TABLE user ADD COLUMN openai_api_key TEXT",
    "ALTER TABLE user ADD COLUMN openai_model VARCHAR(50) DEFAULT 'gpt-4o-mini'",
    "ALTER TABLE mail_assessments ADD COLUMN replied_at DATETIME",
    "ALTER TABLE todo ADD COLUMN priority VARCHAR(10) DEFAULT 'MEDIUM'",
    "ALTER TABLE user ADD COLUMN slack_bot_token TEXT",
    "ALTER TABLE user ADD COLUMN slack_channel_id VARCHAR(100)",
    "ALTER TABLE user ADD COLUMN weekly_report_enabled BOOLEAN DEFAULT 0",
  ]
  with engine.connect() as conn:
    for sql in migrations:
      try:
        conn.execute(text(sql))
        conn.commit()
      except Exception:
        pass  # カラムが既に存在する場合は無視

if __name__ == "__main__":
  create_tables()