# with_structured_output で利用するPydanticスキーマ定義

from pydantic import BaseModel, Field
from datetime import date
from typing import Optional
from datetime import datetime
from uuid import uuid4

from db.engine import TodoStatus, TagType

class AttachmentMeta(BaseModel):
  attachment_id: str = Field(..., description="Gmail APIの添付ファイルID")
  filename: str = Field(..., description="ファイル名")
  mime_type: Optional[str] = Field(default=None, description="MIMEタイプ")
  size: Optional[int] = Field(default=None, description="ファイルサイズ（バイト）")

class Mail(BaseModel):
  id: str = Field(default_factory=lambda: str(uuid4()))
  from_name: Optional[str] = Field(default=None, nullable=True ,description="送り人名")
  from_email: Optional[str] = Field(default=None, nullable=True , description="送信元メールアドレス")
  to_name: Optional[str] = Field(default=None, nullable=True , description="宛先名")
  to_email: Optional[str] = Field(default=None,  nullable=True , description="宛先メールアドレス")
  title: Optional[str] = Field(default=None, nullable=True ,  description="メールタイトル")
  body: Optional[str] = Field(default=None,  nullable=True , description="メール本文")
  has_attachments: Optional[bool] = Field(default=False, description="添付ファイル有無")
  attachments: list[AttachmentMeta] = Field(default_factory=list, description="添付ファイル一覧")
  day: Optional[date] = Field(default=None, description="送信日")

class MailAIAnalysis(BaseModel):
  mail_id: str = Field(..., description="対象メールID")
  tag: TagType = Field(..., description="分類結果")
  summary: str = Field(..., description="要約結果（必ず日本語で記述）")
  reason: Optional[str] = Field(
    default=None,
    description="判定理由を100文字以内で簡潔に日本語で記述"
  )
  needs_immediate_reply: bool = Field(
    ...,
    description="即時返信が必要かどうか"
  )
  extracted_deadline: Optional[datetime] = Field(
    default=None,
    description="本文から抽出された期限（存在しない場合はNone）"
  )
  ai_response_message: Optional[str] = Field(
    default="",
    description="元メールに対してAIが生成した返信用メッセージ（100文字以内）"
  )
  model_name: Optional[str] = Field(
    default=None,
    description="使用したAIモデル名"
  )
  analyzed_at: datetime = Field(
    default_factory=datetime.now,
    description="解析日時"
  )
  should_create_todo: bool  = Field(default=False, description="TODOとして登録すべきかどうかを示すフラグ") #TODOリストに登録させるためのフラグ。

class AnalyzedMail(BaseModel):
  mail: Mail
  mail_ai_analysis: MailAIAnalysis

class TodoCreate(BaseModel):
  id: str = Field(default_factory=lambda: str(uuid4()))
  title: str = Field(..., description="タイトル", example="資料作成")
  body: str = Field(..., description="詳細内容", example="クライアント向け資料を作る")
  created_at: datetime = Field(..., description="作成日時", example="2026-04-26T12:00:00")
  user_id: str = Field(..., description="ユーザーID", example="1c6fa8d2-3c4b-4e2a-9f5a-123456789abc")
  status: TodoStatus = Field(..., description="ステータス", example="未対応")

  class Config:
    from_attributes = True
