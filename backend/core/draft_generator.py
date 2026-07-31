import logging
from pydantic import BaseModel, Field
from local_llm_base import LlmBase

logger = logging.getLogger(__name__)

class MailDraftSchema(BaseModel):
  draft: str = Field(..., description="生成した返信メール本文（日本語、200〜400文字）")

class MailDraftGenerator(LlmBase):
  def __init__(self, provider: str = "local", api_key: str | None = None,
                llm_model: str | None = None):
    prompt = """あなたは丁寧な日本語ビジネスメールを書く専門家です。
              以下のメールに対する返信文を作成してください。
              送信者: {from_name} <{from_email}>
              件名: {title}
              本文:
              {body}
              要件:
              - 日本語で書くこと
              - ビジネスメールとして適切な丁寧さを保つこと
              - 件名・宛先は含めず、本文のみ出力すること
              - 200〜400文字程度で簡潔にまとめること
              # 出力ルール（厳守）
              - 返信本文そのものだけを出力すること。
              - 前置き・説明・メタ的な文を一切付けないこと。
                禁止例:「以下のような返信文を作成しました」「返信文は次の通りです」
                「了解しました」「こちらが返信です」など。
              - 末尾に補足やコメントを付けないこと。
              - 件名や宛名の要否は本文の流れに従い、不要な定型句は足さないこと。
              - 出力は返信メールとしてそのまま送信できる状態にすること。"""
    super().__init__(prompt=prompt, structured_model=MailDraftSchema, temperature=0.7,
                      provider=provider, api_key=api_key, model_name=llm_model)

  def generate(self, from_name: str, from_email: str, title: str, body: str) -> str:
    result: MailDraftSchema = self.chain.invoke({
      "from_name": from_name,
      "from_email": from_email,
      "title": title,
      "body": body,
    })
    logger.debug("Draft generated for subject: %s", title)
    return result.draft
