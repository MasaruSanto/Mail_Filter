from llm_schemas import TodoCreate, AnalyzedMail

from local_llm_base import LlmBase

class TodoService(LlmBase):
  def __init__(self, provider: str = "local", api_key: str | None = None,
               llm_model: str | None = None):
    prompt = """
    以下の内容をTODOリストにしてください。
    日本語で出力をしてください。英語は使用しないこと。
    タイトル: {title}
    本文: {body}
    user_id"{user_id}"を使用してください。
    """
    super().__init__(prompt=prompt, structured_model=TodoCreate,
                     provider=provider, api_key=api_key, model_name=llm_model)

  def create(self, analyzed_mail: AnalyzedMail, user_id:str) -> TodoCreate:
    result: TodoCreate = self.chain.invoke({
      "title": analyzed_mail.mail.title,
      "body": analyzed_mail.mail.body,
      "user_id": user_id,
    })
    return result
  