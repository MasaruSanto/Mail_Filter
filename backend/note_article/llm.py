# LLMプロバイダの切り替え（claude / openai / local）

_PROVIDER_DEFAULTS: dict[str, dict] = {
  "local": {
    "base_url": "http://localhost:1234/v1",
    "api_key": "not-needed",
    "model_name": "openai/gpt-oss-20b",
  },
  "openai": {
    "model_name": "gpt-4o-mini",
  },
  "claude": {
    "model_name": "claude-sonnet-5",
  },
}


def get_chat_model(provider: str = "claude", api_key: str | None = None,
                    model_name: str | None = None, temperature: float = 0.3,
                    max_tokens: int = 8192):
  """provider に応じたLangChainのチャットモデルを返す"""
  defaults = _PROVIDER_DEFAULTS[provider]
  resolved_model = model_name or defaults["model_name"]

  if provider == "claude":
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
      model=resolved_model,
      api_key=api_key,
      temperature=temperature,
      max_tokens=max_tokens,
    )

  from langchain_openai import ChatOpenAI
  config = {
    **defaults,
    "api_key": api_key or defaults.get("api_key"),
    "model_name": resolved_model,
    "temperature": temperature,
    "max_tokens": max_tokens,
  }
  return ChatOpenAI(**config)


def with_structured(llm, provider: str, schema):
  """構造化出力の呼び出し方式の差異を吸収する

  LM Studioのローカルモデルはjson_schema方式に対応していないことが多いため
  function_calling方式を使う。OpenAIはjson_schema方式が安定して動く。
  """
  if provider == "local":
    return llm.with_structured_output(schema, method="function_calling", tool_choice="auto")
  if provider == "openai":
    return llm.with_structured_output(schema, method="json_schema")
  return llm.with_structured_output(schema)
