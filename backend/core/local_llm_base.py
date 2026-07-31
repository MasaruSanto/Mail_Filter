from abc import ABC
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

_PROVIDER: dict[str, dict] = {
    "local": {
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "model_name": "openai/gpt-oss-20b",
    },
    "openai": {
        "model_name": "gpt-4o-mini",
    },
}

class LlmBase(ABC):
  def __init__(self, prompt: str, structured_model: BaseModel,
               frequency_penalty: float = 0.3, presence_penalty: float = 0.1,
               temperature: float = 0.2, max_tokens: int = 4096,
               provider: str = "local", api_key: str | None = None,
               model_name: str | None = None):
    super().__init__()
    resolved_model = model_name or _PROVIDER[provider]["model_name"]
    config = {
      **_PROVIDER[provider],
      "api_key": api_key or _PROVIDER[provider].get("api_key"),
      "model_name": resolved_model,
      "max_tokens": max_tokens,
    }
    if not self._is_reasoning_model(resolved_model):
      config["temperature"] = temperature
      config["model_kwargs"] = {
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
      }
    prompt_template = ChatPromptTemplate.from_template(prompt)
    llm = ChatOpenAI(**config)
    if provider == "local":
      structured_llm = llm.with_structured_output(
        structured_model,
        method="function_calling",
        tool_choice="auto",
      )
    else:
      structured_llm = llm.with_structured_output(
        structured_model,
        method="json_schema",
      )
    self.chain = prompt_template | structured_llm
  
  @staticmethod
  def _is_reasoning_model(model_name: str) -> bool:
    """gpt-5系・o系のreasoningモデルは temperature / penalty 系パラメータを受け付けない"""
    return model_name.startswith(("gpt-5", "o1", "o3", "o4"))
