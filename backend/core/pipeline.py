# Gmailからメールを取得し、AI分析してDBに保存するまでの一連のフローを管理する

import logging
import os
import sys

logger = logging.getLogger(__name__)

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for p in (project_path, os.path.dirname(__file__)):
  if p not in sys.path:
    sys.path.insert(0, p)

from core.google.mail_client import GoogleMailClient
from core.google.calendar_client import GoogleCalendarClient
from core.google.repository import MailRepository, CalendarRepository
from parser import GmailParser
from pretreatment import Pretreatment
from classifier import MailClassifier
from todo_service import TodoService
from db.engine import SessionLocal
from db.query import save_mail, save_mail_assessment, save_todo

MAX_BODY_CHARS = 4000

class MailPipeline:

  def __init__(self, user_id: str, refresh_token: str, max_results: int = 3,
               after_days: int | None = None, extra_instruction: str = "",
               llm_provider: str = "local", llm_api_key: str | None = None,
               llm_model: str | None = None):
    self._user_id = user_id
    self._max_results = max_results
    self._after_days = after_days
    self._refresh_token = refresh_token
    self._mail_repo = MailRepository(GoogleMailClient(refresh_token=refresh_token))
    self._parser = GmailParser()
    self._pretreatment = Pretreatment()
    self._classifier = MailClassifier(extra_instruction=extra_instruction,
                                      provider=llm_provider, api_key=llm_api_key,
                                      llm_model=llm_model)
    self._todo_generator = TodoService(provider=llm_provider, api_key=llm_api_key,
                                       llm_model=llm_model)
    self.urgent_mails: list[str] = []

  def run(self) -> tuple[int, list[str]]:
    db = SessionLocal()
    processed = 0
    errors: list[str] = []
    self.urgent_mails = []
    try:
      after_date = None
      if self._after_days:
        from datetime import date, timedelta
        after_date = date.today() - timedelta(days=self._after_days)
      message_ids = self._mail_repo.fetch_id_list(max_results=self._max_results, after_date=after_date)
      logger.info("%d件のメールを取得", len(message_ids))

      for mid in message_ids:
        try:
          self._process_one(db, mid)
          processed += 1
        except Exception as e:
          msg = f"{type(e).__name__}: {e}"
          logger.warning("処理失敗 (%s): %s", mid, msg)
          errors.append(msg)
          db.rollback()

    finally:
      db.close()
    return processed, errors

  def _process_one(self, db, message_id: str) -> None:
    # 1. Gmail APIからメール詳細を取得
    raw = self._mail_repo.fetch(message_id)

    # 2. Gmail APIレスポンス → Mailスキーマに変換
    mail = self._parser.parse(raw)

    # 3. 本文を前処理
    mail.body = self._pretreatment.process(mail.body)

    # 4. DBに保存（既存ならそのまま返す）
    db_mail = save_mail(db, mail, self._user_id)
    logger.debug("メール保存: %s", mail.title)

    # is_analyzed フラグまたは assessment レコードが既に存在する場合はスキップ
    if db_mail.is_analyzed or db_mail.assessment:
      logger.debug("スキップ: 既に分析済み (%s)", mail.title)
      return

    # 本文が空ならスキップ
    if not mail.body or not mail.body.strip():
      logger.debug("スキップ: 本文が空 (%s)", mail.title)
      return

    # 5. AIで分類・要約
    try:
      analyzed = self._classifier.classify(mail)

      if analyzed.mail_ai_analysis.should_create_todo:
        todo = self._todo_generator.create(analyzed_mail=analyzed, user_id=self._user_id)
        save_todo(db, self._user_id, todo, analyzed.mail_ai_analysis.extracted_deadline)

      save_mail_assessment(db, mail.id, analyzed.mail_ai_analysis)

      if analyzed.mail_ai_analysis.needs_immediate_reply:
        self.urgent_mails.append(mail.title or "(件名なし)")

      # 期限が抽出された場合はGoogleカレンダーにイベント登録
      if analyzed.mail_ai_analysis.extracted_deadline:
        self._register_calendar_event(mail, analyzed.mail_ai_analysis)

    except Exception as e:
      db.rollback()
      logger.warning("AI分析失敗（メールは保存済み）[%s]: %s", mail.title, e)
      raise RuntimeError(f"AI分析失敗 [{mail.title}]: {e}") from e


  def _register_calendar_event(self, mail, analysis) -> None:
    from datetime import timedelta
    try:
      cal_client = GoogleCalendarClient(refresh_token=self._refresh_token)
      cal_repo = CalendarRepository(cal_client)
      deadline = analysis.extracted_deadline
      cal_repo.create_event(
        summary=mail.title or "(件名なし)",
        location="",
        start=deadline,
        end=deadline + timedelta(hours=1),
        description=analysis.summary,
      )
      logger.info("カレンダー登録完了: %s (%s)", mail.title, deadline)
    except Exception as e:
      logger.warning("カレンダー登録失敗（スキップ）: %s", e)


if __name__ == "__main__":
  pipeline = MailPipeline(max_results=5, user_id=1)
  pipeline.run()
