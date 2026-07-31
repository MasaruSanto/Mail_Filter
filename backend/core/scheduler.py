import logging
import os
import sys

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (project_path, os.path.dirname(__file__)):
  if p not in sys.path:
    sys.path.insert(0, p)

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from db.engine import SessionLocal, User
from pipeline import MailPipeline
from crypto import decrypt, decrypt_or_plain
from slack import Slack
from weekly_report import send_weekly_report

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(
  timezone="Asia/Tokyo",
  job_defaults={
    "coalesce": True,        # 実行漏れは最新1回のみ実行（積み上げ防止）
    "max_instances": 1,      # 同一ジョブの重複実行を禁止
    "misfire_grace_time": 300,  # 5分以内の遅延なら実行を試みる
  },
)

VALID_INTERVALS = {5, 10, 30, 60}


def _on_job_error(event) -> None:
  logger.error(
    "[Scheduler] ジョブ実行エラー job_id=%s: %s",
    event.job_id,
    event.exception,
    exc_info=(type(event.exception), event.exception, event.traceback),
  )

def _on_job_missed(event) -> None:
  logger.warning("[Scheduler] ジョブ実行漏れ job_id=%s", event.job_id)


def _notify_slack(
  user_email: str,
  urgent_mails: list[str],
  encrypted_token: str | None,
  channel_id: str | None,
) -> None:
  if not encrypted_token or not channel_id:
    return
  try:
    token = decrypt_or_plain(encrypted_token)
    lines = "\n".join(f"  • {title}" for title in urgent_mails)
    text = f"*[MailAI] 要返信メールが{len(urgent_mails)}件あります* ({user_email})\n{lines}"
    Slack(token=token, channel=channel_id).post_message(text)
  except Exception as e:
    logger.warning("[Scheduler] Slack通知失敗: %s", e)

def _run_pipeline(user_id: str) -> None:
  db = SessionLocal()
  try:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_refresh_token:
      return
    pipeline = MailPipeline(
      user_id=user_id,
      refresh_token=decrypt_or_plain(user.google_refresh_token),
      max_results=10,
      after_days=1,
      extra_instruction=user.prompt_instruction or "",
      llm_provider=user.llm_provider or "local",
      llm_api_key=decrypt(user.openai_api_key) if user.openai_api_key else None,
      llm_model=user.openai_model,
    )
    processed, errors = pipeline.run()
    logger.info("[Scheduler] %s: %d件処理, エラー%d件", user.email, processed, len(errors))
    if errors:
      for err in errors:
        logger.warning("[Scheduler] pipeline partial error (%s): %s", user.email, err)

    if pipeline.urgent_mails:
      _notify_slack(
        user.email,
        pipeline.urgent_mails,
        user.slack_bot_token,
        user.slack_channel_id,
      )

  except Exception as e:
    logger.error("[Scheduler] pipeline error (user=%s): %s", user_id, e, exc_info=True)
  finally:
    db.close()

def _run_weekly_report(user_id: str) -> None:
  db = SessionLocal()
  try:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
      return
    send_weekly_report(db, user)
    logger.info("[Scheduler] 週次レポート送信: %s", user.email)
  except Exception as e:
    logger.error("[Scheduler] 週次レポート送信失敗 (user=%s): %s", user_id, e, exc_info=True)
  finally:
    db.close()

def schedule_weekly_report(user_id: str) -> None:
  job_id = f"weekly_report_{user_id}"
  _scheduler.add_job(
    _run_weekly_report,
    trigger=CronTrigger(day_of_week="mon", hour=9, minute=0),
    id=job_id,
    args=[user_id],
    replace_existing=True,
  )
  logger.info("[Scheduler] 週次レポート有効化: user=%s", user_id)

def unschedule_weekly_report(user_id: str) -> None:
  job_id = f"weekly_report_{user_id}"
  if _scheduler.get_job(job_id):
    _scheduler.remove_job(job_id)
    logger.info("[Scheduler] 週次レポート無効化: user=%s", user_id)

def schedule_user(user_id: str, interval_minutes: int) -> None:
  job_id = f"pipeline_{user_id}"
  if interval_minutes in VALID_INTERVALS:
    _scheduler.add_job(
      _run_pipeline,
      trigger=IntervalTrigger(minutes=interval_minutes),
      id=job_id,
      args=[user_id],
      replace_existing=True,
    )
    logger.info("[Scheduler] scheduled user=%s every %dmin", user_id, interval_minutes)

def unschedule_user(user_id: str) -> None:
  job_id = f"pipeline_{user_id}"
  if _scheduler.get_job(job_id):
    _scheduler.remove_job(job_id)
    logger.info("[Scheduler] unscheduled user=%s", user_id)

def load_all_schedules(db) -> None:
  users = db.query(User).all()
  count = 0
  for user in users:
    minutes_str = user.pipeline_schedule_minutes
    if minutes_str and minutes_str.isdigit():
      minutes = int(minutes_str)
      if minutes in VALID_INTERVALS:
        schedule_user(str(user.id), minutes)
        count += 1
    if user.weekly_report_enabled:
      schedule_weekly_report(str(user.id))
  logger.info("[Scheduler] %dユーザーのスケジュールをロードしました", count)

def start() -> None:
  _scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
  _scheduler.add_listener(_on_job_missed, EVENT_JOB_MISSED)
  _scheduler.start()
  logger.info("[Scheduler] 起動完了")

def shutdown() -> None:
  if _scheduler.running:
    _scheduler.shutdown(wait=True)  # 実行中ジョブの完了を待つ
    logger.info("[Scheduler] シャットダウン完了")
