from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import datetime, date
import os
import sys

# backend/ と backend/core/ をパスに追加
project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
core_path = os.path.join(project_path, 'core')
for p in (project_path, core_path):
  if p not in sys.path:
    sys.path.insert(0, p)

from db.engine import Mail as DBMail, MailAssessment as DBMailAssessment, MailAttachment as DBMailAttachment
from db.engine import TODO as DBTODO
from core.llm_schemas import Mail as LLMMail, MailAIAnalysis
from core.llm_schemas import TodoCreate
from core.enums import TagType

# --- 読み込み ---

def get_all_mails(db: Session, user_id: str) -> list[DBMail]:
  return (
    db.query(DBMail)
    .filter(DBMail.user_id == user_id)
    .order_by(DBMail.day.desc(), DBMail.created_at.desc())
    .all()
  )

def search_mails(
  db: Session,
  user_id: str,
  q: str | None = None,
  from_email: str | None = None,
  tag: str | None = None,
  needs_reply: bool | None = None,
  is_analyzed: bool | None = None,
  has_attachments: bool | None = None,
  date_from: date | None = None,
  date_to: date | None = None,
  limit: int = 50,
  offset: int = 0,
) -> tuple[list[DBMail], int]:
  query = (
    db.query(DBMail)
    .options(joinedload(DBMail.assessment))
    .filter(DBMail.user_id == user_id)
  )

  if q:
    keyword = f"%{q}%"
    query = query.filter(
      or_(
        DBMail.from_name.ilike(keyword),
        DBMail.from_email.ilike(keyword),
        DBMail.title.ilike(keyword),
        DBMail.body.ilike(keyword),
      )
    )

  if from_email:
    query = query.filter(DBMail.from_email == from_email)

  if is_analyzed is not None:
    query = query.filter(DBMail.is_analyzed == is_analyzed)

  if has_attachments is not None:
    query = query.filter(DBMail.has_attachments == has_attachments)

  if date_from:
    query = query.filter(DBMail.day >= datetime.combine(date_from, datetime.min.time()))

  if date_to:
    query = query.filter(DBMail.day <= datetime.combine(date_to, datetime.max.time()))

  if tag or needs_reply is not None:
    query = query.join(DBMailAssessment)
    if tag:
      try:
        query = query.filter(DBMailAssessment.priority == TagType(tag))
      except ValueError:
        pass
    if needs_reply is not None:
      query = query.filter(DBMailAssessment.needs_immediate_reply == needs_reply)

  query = query.order_by(DBMail.day.desc(), DBMail.created_at.desc())
  total = query.count()
  mails = query.offset(offset).limit(limit).all()
  return mails, total


def get_mail_detail(db: Session, mail_id: str, user_id: str | None = None) -> DBMail | None:
  q = (
    db.query(DBMail)
    .options(joinedload(DBMail.assessment), joinedload(DBMail.attachments))
    .filter(DBMail.id == str(mail_id))
  )
  if user_id is not None:
    q = q.filter(DBMail.user_id == user_id)
  return q.first()

def get_todo_list(db:Session, user_id:str) -> list[DBTODO]:
  #ユーザーIDを使いTODOリストを取得
  return (
    db.query(DBTODO)
    .filter(DBTODO.user_id == user_id)
    .order_by(DBTODO.created_at.desc())
    .all()
  )

def get_todo(db: Session, todo_id: str, user_id: str) -> DBTODO | None:
  return (
    db.query(DBTODO)
    .filter(DBTODO.id == todo_id, DBTODO.user_id == user_id)
    .first()
  )


# --- 書き込み ---

def save_mail(db: Session, mail: LLMMail, user_id: str) -> DBMail:
  # まずこのユーザーのレコードを検索
  existing = db.query(DBMail).filter(
    DBMail.id == str(mail.id),
    DBMail.user_id == user_id,
  ).first()
  if existing:
    return existing

  # user_id=NULL の旧レコードのみ現在のユーザーに引き継ぐ
  # （他ユーザー所有のレコードを奪わないよう user_id IS NULL に限定する）
  orphan = db.query(DBMail).filter(
    DBMail.id == str(mail.id),
    DBMail.user_id.is_(None),
  ).first()
  if orphan:
    orphan.user_id = user_id
    db.commit()
    return orphan

  db_mail = DBMail(
    id=str(mail.id),
    from_name=mail.from_name,
    from_email=mail.from_email,
    to_name=mail.to_name,
    to_email=mail.to_email,
    title=mail.title,
    body=mail.body,
    has_attachments=mail.has_attachments or False,
    day=mail.day,
    user_id=user_id,
  )
  db.add(db_mail)
  db.commit()
  db.refresh(db_mail)

  for att in mail.attachments:
    db.add(DBMailAttachment(
      mail_id=db_mail.id,
      attachment_id=att.attachment_id,
      filename=att.filename,
      mime_type=att.mime_type,
      size=att.size,
    ))
  if mail.attachments:
    db.commit()

  return db_mail

def save_mail_assessment(db: Session, mail_id: str, analysis: MailAIAnalysis) -> DBMailAssessment:
  # 既存レコードがあれば上書き、なければ新規作成（UPSERT）
  assessment = db.query(DBMailAssessment).filter(DBMailAssessment.mail_id == str(mail_id)).first()
  if assessment:
    assessment.summarized_body = analysis.summary
    assessment.priority = analysis.tag
    assessment.needs_immediate_reply = analysis.needs_immediate_reply
    assessment.reason = analysis.reason or ""
    assessment.extracted_deadline = analysis.extracted_deadline
    assessment.ai_response_message = analysis.ai_response_message or ""
  else:
    assessment = DBMailAssessment(
      mail_id=str(mail_id),
      summarized_body=analysis.summary,
      priority=analysis.tag,
      needs_immediate_reply=analysis.needs_immediate_reply,
      reason=analysis.reason or "",
      extracted_deadline=analysis.extracted_deadline,
      ai_response_message=analysis.ai_response_message or "",
    )
    db.add(assessment)

  db.query(DBMail).filter(DBMail.id == str(mail_id)).update({"is_analyzed": True})
  db.commit()
  db.refresh(assessment)
  return assessment

def save_todo(db:Session, user_id:str, llm_todo:TodoCreate, due_date: datetime | None) -> DBTODO:
  #DB TODO内容を登録。
  todo = DBTODO(
    title=llm_todo.title,
    body=llm_todo.body,
    status=llm_todo.status,
    due_date=due_date,
    user_id=user_id
  )
  db.add(todo)
  db.commit()
  db.refresh(todo)
  return todo


if __name__ == "__main__":
  from db.engine import SessionLocal

  db = SessionLocal()
  try:
    mails = get_all_mails(db)
    print(f"=== 全メール一覧 ({len(mails)}件) ===")
    for m in mails:
      print(f"  [{m.day}] {m.from_name} / {m.title}")

    if mails:
      detail = get_mail_detail(db, str(mails[0].id))
      print(f"\n=== 詳細 ===")
      print(f"  タイトル   : {detail.title}")
      print(f"  送信者     : {detail.from_name} <{detail.from_email}>")
      print(f"  添付ファイル: {detail.has_attachments}")
      if detail.assessment:
        print(f"  優先度     : {detail.assessment.priority}")
        print(f"  要約       : {detail.assessment.summarized_body}")
  finally:
    db.close()
