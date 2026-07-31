# Gmail APIのレスポンス（dict）をllm_schemas.Mailに変換するパーサー

import base64
from datetime import date
from email.utils import parseaddr, parsedate_to_datetime
from uuid import uuid4

from llm_schemas import Mail, AttachmentMeta


class GmailParser:

  def parse(self, raw: dict) -> Mail:
    headers = self._extract_headers(raw)
    from_name, from_email = parseaddr(headers.get("From", ""))
    to_name, to_email = parseaddr(headers.get("To", ""))

    payload = raw.get("payload", {})
    body = self._extract_body(payload)
    attachments = self._extract_attachments(payload)
    day = self._parse_date(headers.get("Date"))

    gmail_id = raw.get("id") or str(uuid4())

    return Mail(
      id=gmail_id,
      from_name=from_name or None,
      from_email=from_email or None,
      to_name=to_name or None,
      to_email=to_email or None,
      title=headers.get("Subject"),
      body=body,
      has_attachments=bool(attachments),
      attachments=attachments,
      day=day,
    )

  # --- private helpers ---

  def _extract_headers(self, raw: dict) -> dict[str, str]:
    # ヘッダーリストをキーで引けるdictに変換
    headers = raw.get("payload", {}).get("headers", [])
    return {h["name"]: h["value"] for h in headers}

  def _extract_body(self, payload: dict) -> str | None:
    mime_type = payload.get("mimeType", "")

    if mime_type.startswith("multipart/"):
      # multipart の場合は parts を再帰的に探索
      return self._extract_from_parts(payload.get("parts", []))

    if mime_type in ("text/plain", "text/html"):
      return self._decode_data(payload.get("body", {}).get("data", ""))

    return None

  def _extract_from_parts(self, parts: list) -> str | None:
    # text/plain を優先し、なければ text/html を使う
    plain = None
    html = None
    for part in parts:
      mime_type = part.get("mimeType", "")
      if mime_type == "text/plain":
        plain = self._decode_data(part.get("body", {}).get("data", ""))
      elif mime_type == "text/html":
        html = self._decode_data(part.get("body", {}).get("data", ""))
      elif mime_type.startswith("multipart/"):
        result = self._extract_from_parts(part.get("parts", []))
        if result:
          return result
    return plain or html

  def _decode_data(self, data: str) -> str | None:
    # Gmail APIはbody dataをbase64url方式でエンコードしている
    if not data:
      return None
    decoded = base64.urlsafe_b64decode(data + "==")
    text = decoded.decode("utf-8", errors="replace")
    # 改行コードを\nに統一（\r\n, \rが混在するとSSR/CSRで表示が食い違うため）
    return text.replace("\r\n", "\n").replace("\r", "\n")

  def _extract_attachments(self, payload: dict) -> list[AttachmentMeta]:
    # filenameとattachmentIdが両方存在するpartを添付ファイルとみなす（再帰）
    results: list[AttachmentMeta] = []
    for part in payload.get("parts", []):
      filename = part.get("filename")
      body = part.get("body", {})
      attachment_id = body.get("attachmentId")
      if filename and attachment_id:
        results.append(AttachmentMeta(
          attachment_id=attachment_id,
          filename=filename,
          mime_type=part.get("mimeType"),
          size=body.get("size"),
        ))
      results.extend(self._extract_attachments(part))
    return results

  def _parse_date(self, date_str: str | None) -> date | None:
    if not date_str:
      return None
    try:
      return parsedate_to_datetime(date_str).date()
    except Exception:
      return None


if __name__ == "__main__":
  # fetch()の戻り値を模したサンプルデータでテスト
  sample_raw = {
    "payload": {
      "headers": [
        {"name": "From", "value": "山田 太郎 <yamada@example.com>"},
        {"name": "To", "value": "自分 <me@example.com>"},
        {"name": "Subject", "value": "テストメール"},
        {"name": "Date", "value": "Mon, 01 Jan 2024 12:00:00 +0900"},
      ],
      "mimeType": "multipart/alternative",
      "parts": [
        {
          "mimeType": "text/plain",
          # base64url("こんにちは！")
          "body": {"data": base64.urlsafe_b64encode("こんにちは！".encode()).decode()},
        }
      ],
    }
  }

  parser = GmailParser()
  mail = parser.parse(sample_raw)
  print("=== パース結果 ===")
  print(f"  from : {mail.from_name} <{mail.from_email}>")
  print(f"  to   : {mail.to_name} <{mail.to_email}>")
  print(f"  title: {mail.title}")
  print(f"  body : {mail.body}")
  print(f"  day  : {mail.day}")
  print(f"  attach: {mail.has_attachments}")
