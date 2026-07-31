import re
import json
import time

from llm_schemas import Mail, MailAIAnalysis, AnalyzedMail
from pydantic import ValidationError

from local_llm_base import LlmBase

# UUID パターン（mail_id などが混入した場合に除去）
_UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE)
# JSON キー・値フラグメント（例: "mail_id": "..."）
_JSON_KV_RE = re.compile(r'"[^"]{1,40}"\s*:\s*(?:"[^"]*"|\d+|true|false|null)')
# 残った JSON 構造記号
_JSON_SYMBOL_RE = re.compile(r'[{}\[\]]')

def _sanitize(text: str | None) -> str:
  if not text:
    return ""
  # テキスト全体が JSON オブジェクトの場合、中身を結合して取り出す
  stripped = text.strip()
  if stripped.startswith("{") and stripped.endswith("}"):
    try:
      obj = json.loads(stripped)
      # summary / reason / body など文字列値を優先的に返す
      for key in ("summary", "reason", "body", "text", "content"):
        if key in obj and isinstance(obj[key], str):
          return obj[key].strip()
      # 文字列値があれば最初のものを返す
      for v in obj.values():
        if isinstance(v, str) and len(v) > 5:
          return v.strip()
    except (json.JSONDecodeError, ValueError):
      pass
  # UUID を除去
  text = _UUID_RE.sub("", text)
  # JSON キー・値フラグメントを除去
  text = _JSON_KV_RE.sub("", text)
  # 残った JSON 記号を除去
  text = _JSON_SYMBOL_RE.sub("", text)
  # 連続スペース・改行を整理
  text = re.sub(r'[ \t]{2,}', ' ', text)
  text = re.sub(r'\n{3,}', '\n\n', text)
  return text.strip()

class MailClassifier(LlmBase):
  def __init__(self, extra_instruction: str = "", provider: str = "local",
               api_key: str | None = None, llm_model: str | None = None):
    prompt = """
    以下のメールを分類してください。
    summary・reason は必ず日本語で出力してください。英語は使用しないこと。
    送信者: {from_name} <{from_email}>
    タイトル: {title}
    本文: {body}
    添付ファイル: {has_attachments}
    mail_idは"{mail_id}"を使用してください。

    should_create_todoの判断基準:
    - 返信・対応・確認など何らかのアクションが必要 → true
    - 期限・締め切りが含まれている → true
    - 迷惑メール・営業メール・読むだけでよいメール → false
    """
    if extra_instruction and extra_instruction.strip():
      prompt += f"\n\n【追加指示】\n{extra_instruction.strip()}"
    super().__init__(prompt=prompt, structured_model=MailAIAnalysis,
                     provider=provider, api_key=api_key, model_name=llm_model)

  def classify(self, mail: Mail) -> AnalyzedMail:
    last_err = None
    for attempt in range(3):
      try:
        classification: MailAIAnalysis = self.chain.invoke({
          "from_name": mail.from_name or "",
          "from_email": mail.from_email or "",
          "title": mail.title or "",
          "body": mail.body or "",
          "has_attachments": mail.has_attachments,
          "mail_id": mail.id,
        })
        classification.summary = _sanitize(classification.summary)
        classification.reason = _sanitize(classification.reason)

        return AnalyzedMail(mail=mail, mail_ai_analysis=classification)

      except (ValidationError, Exception) as e:
        wait = 2 ** attempt  # 1s → 2s → 4s
        print(f"⚠ 試行 {attempt+1}/3 失敗 ({type(e).__name__}): {e} → {wait}秒後にリトライ")
        last_err = e
        if attempt < 2:
          time.sleep(wait)

    raise RuntimeError(f"3回試行しても分類失敗: {last_err}")

if __name__ == "__main__":
  mail = Mail()
  classifier = MailClassifier()
  analyzed_mail = classifier.classify(mail=mail)
  print(analyzed_mail)