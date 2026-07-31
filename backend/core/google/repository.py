import base64
from datetime import datetime, timezone
from email.mime.text import MIMEText

from googleapiclient.errors import HttpError

from core.google.error import CalendarError, GoogleApiError, MailFetchError, MailSendError
from core.google.calendar_client import GoogleCalendarClient
from core.google.mail_client import GoogleMailClient
from core.google.people_client import GooglePeopleClient

class CalendarRepository:
  def __init__(self, client: GoogleCalendarClient):
    self._client = client

  def _to_rfc3339(self, dt: datetime) -> str:
    """Google Calendar API用にdatetimeをRFC3339形式に変換"""
    if dt.tzinfo is None:
      dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

  def delete_event(self, event_id: str) -> bool:
    try:
      self._client.service.events().delete(
        calendarId="primary", eventId=event_id
      ).execute()
      return True
    except HttpError as e:
      raise CalendarError(e, "削除")

  def create_event(
    self,
    summary: str,
    location: str,
    start: datetime,
    end: datetime,
    description: str | None = None,
  ) -> dict:
    body = {
      "summary": summary,
      "location": location,
      "start": {"dateTime": self._to_rfc3339(start)},
      "end": {"dateTime": self._to_rfc3339(end)},
    }
    if description is not None:
      body["description"] = description

    try:
      return self._client.service.events().insert(
        calendarId="primary", body=body
      ).execute()
    except HttpError as e:
      raise CalendarError(e, "作成")

  def update_event(
    self,
    event_id: str,
    summary: str,
    location: str,
    start: datetime,
    end: datetime,
    description: str | None = None,
  ) -> dict:
    body = {
      "summary": summary,
      "location": location,
      "start": {"dateTime": self._to_rfc3339(start)},
      "end": {"dateTime": self._to_rfc3339(end)},
    }
    if description is not None:
      body["description"] = description

    try:
      return self._client.service.events().update(
        calendarId="primary", eventId=event_id, body=body
      ).execute()
    except HttpError as e:
      raise CalendarError(e, "更新")

  def fetch_events(
    self,
    max_results: int,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
  ) -> list:
    params: dict = {
      "calendarId": "primary",
      "maxResults": max_results,
      "singleEvents": True,
      "orderBy": "startTime",
    }
    if time_min is not None:
      params["timeMin"] = self._to_rfc3339(time_min)
    if time_max is not None:
      params["timeMax"] = self._to_rfc3339(time_max)

    try:
      result = self._client.service.events().list(**params).execute()
      return result.get("items", [])
    except HttpError as e:
      raise CalendarError(e, "取得")

class MailRepository:
  def __init__(self, client: GoogleMailClient):
    self._client = client

  def fetch_id_list(self, max_results: int, after_date=None) -> list[str]:
    "指定件数分のメールIDリストを取得する。after_date(date)を渡すとそれ以降のメールに絞る"
    query_parts = ["category:primary"]
    if after_date is not None:
      query_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")
    params: dict = {"userId": "me", "maxResults": max_results, "q": " ".join(query_parts)}
    try:
      result = self._client.service.users().messages().list(**params).execute()
      return [m["id"] for m in result.get("messages", [])]
    except HttpError as e:
      raise MailFetchError(e) from e

  def fetch(self, message_id: str) -> dict:
    "指定IDのメール詳細を取得する"
    try:
      return self._client.service.users().messages().get(
        userId="me", id=message_id
      ).execute()
    except HttpError as e:
      raise MailFetchError(e) from e

  def fetch_attachment(self, message_id: str, attachment_id: str) -> bytes:
    "指定IDの添付ファイル本体をダウンロードする"
    try:
      result = self._client.service.users().messages().attachments().get(
        userId="me", messageId=message_id, id=attachment_id
      ).execute()
      data = result.get("data", "")
      return base64.urlsafe_b64decode(data + "==")
    except HttpError as e:
      raise MailFetchError(e) from e

  def send_reply(
    self,
    to: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
  ) -> dict:
    "返信メールを送信する"
    msg = MIMEText(body, "plain", "utf-8")
    # ヘッダーインジェクション対策（改行を含むヘッダー値を拒否）
    msg["to"] = to.replace("\r", "").replace("\n", "")
    msg["subject"] = subject.replace("\r", "").replace("\n", "")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload: dict = {"raw": raw}
    if thread_id:
      payload["threadId"] = thread_id
    try:
      return self._client.service.users().messages().send(
        userId="me", body=payload
      ).execute()
    except HttpError as e:
      raise MailSendError(e) from e

class ContactsRepository:
  def __init__(self, client: GooglePeopleClient):
    self._client = client

  def fetch_contacts(self, page_size: int = 200) -> list[dict]:
    """Google コンタクトからメールアドレスを持つ連絡先を取得する"""
    results = []
    page_token = None
    while True:
      params: dict = {
        "resourceName": "people/me",
        "pageSize": page_size,
        "personFields": "names,emailAddresses",
      }
      if page_token:
        params["pageToken"] = page_token
      try:
        resp = self._client.service.people().connections().list(**params).execute()
      except HttpError as e:
        raise GoogleApiError("連絡先取得失敗", e) from e
      for person in resp.get("connections", []):
        emails = person.get("emailAddresses", [])
        names = person.get("names", [])
        name = names[0].get("displayName", "") if names else ""
        for email_entry in emails:
          addr = email_entry.get("value", "")
          if addr:
            results.append({"name": name, "email": addr})
      page_token = resp.get("nextPageToken")
      if not page_token:
        break
    return results

if __name__ == "__main__":
  import sys
  token = sys.argv[1] if len(sys.argv) > 1 else None
  if not token:
    print("使い方: python repository.py <refresh_token>")
    sys.exit(1)
  client = GoogleMailClient(refresh_token=token)
  repo = MailRepository(client=client)
  ids = repo.fetch_id_list(max_results=10)
  for mid in ids:
    print(repo.fetch(mid))
