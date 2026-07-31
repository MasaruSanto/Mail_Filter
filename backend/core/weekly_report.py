import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (project_path, os.path.dirname(__file__)):
  if p not in sys.path:
    sys.path.insert(0, p)

from db.engine import Mail as DBMail, MailAssessment as DBAssessment, TODO as DBTODO, User
from core.google.mail_client import GoogleMailClient
from core.google.repository import MailRepository
from crypto import decrypt_or_plain

REPORT_PERIOD_DAYS = 7

def build_summary(db: Session, user_id: str, days: int = REPORT_PERIOD_DAYS) -> str:
  now = datetime.now()
  since = now - timedelta(days=days)

  total = db.query(DBMail).filter(
    DBMail.user_id == user_id,
    DBMail.created_at >= since,
  ).count()

  needs_reply = (
    db.query(DBAssessment)
    .join(DBMail, DBAssessment.mail_id == DBMail.id)
    .filter(
      DBMail.user_id == user_id,
      DBMail.created_at >= since,
      DBAssessment.needs_immediate_reply == True,
    )
    .count()
  )

  replied = (
    db.query(DBAssessment)
    .join(DBMail, DBAssessment.mail_id == DBMail.id)
    .filter(
      DBMail.user_id == user_id,
      DBMail.created_at >= since,
      DBAssessment.replied_at.isnot(None),
    )
    .count()
  )

  todos_created = db.query(DBTODO).filter(
    DBTODO.user_id == user_id,
    DBTODO.created_at >= since,
  ).count()

  priority_counts = (
    db.query(DBAssessment.priority, func.count(DBAssessment.mail_id))
    .join(DBMail, DBAssessment.mail_id == DBMail.id)
    .filter(DBMail.user_id == user_id, DBMail.created_at >= since)
    .group_by(DBAssessment.priority)
    .all()
  )

  lines = [
    f"【週次メールサマリー】{since.strftime('%Y/%m/%d')} 〜 {now.strftime('%Y/%m/%d')}",
    "",
    f"受信メール数　　: {total}件",
    f"要返信メール数　: {needs_reply}件",
    f"返信済み　　　　: {replied}件",
    f"TODO自動生成数　: {todos_created}件",
  ]

  if priority_counts:
    lines.append("")
    lines.append("■ 優先度別件数")
    for priority, count in priority_counts:
      label = priority.value if hasattr(priority, "value") else priority
      lines.append(f"  {label}: {count}件")

  return "\n".join(lines)


def send_weekly_report(db: Session, user: User) -> None:
  if not user.google_refresh_token:
    raise ValueError("Google連携が必要です")

  summary = build_summary(db, str(user.id))
  mail_client = GoogleMailClient(refresh_token=decrypt_or_plain(user.google_refresh_token))
  repo = MailRepository(mail_client)
  repo.send_reply(to=user.email, subject="週次メールサマリーレポート", body=summary)
