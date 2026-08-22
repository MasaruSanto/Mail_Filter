# note記事自動生成パイプラインのCLIエントリーポイント
#
# 使い方:
#   ANTHROPIC_API_KEY=xxx TAVILY_API_KEY=xxx python main.py "生成AIの業務活用"

import argparse
import logging
import os
import sys

_pkg_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_pkg_dir)
if _backend_dir not in sys.path:
  sys.path.insert(0, _backend_dir)

from note_article.graph import build_graph
from note_article.schemas import GraphState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run(topic: str, provider: str = "claude", api_key: str | None = None,
        model_name: str | None = None) -> GraphState:
  app = build_graph(provider=provider, api_key=api_key, model_name=model_name)
  result = app.invoke(GraphState(topic=topic))
  return result if isinstance(result, GraphState) else GraphState(**result)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="note記事自動生成パイプライン")
  parser.add_argument("topic", help="記事のトピック")
  parser.add_argument("--provider", default="claude", choices=["claude", "openai", "local"])
  parser.add_argument("--model", default=None, help="使用するモデル名（省略時はプロバイダのデフォルト）")
  args = parser.parse_args()

  final_state = run(args.topic, provider=args.provider, model_name=args.model)

  if final_state.errors:
    logger.error("パイプライン中断: %s", "; ".join(final_state.errors))
    sys.exit(1)

  if final_state.warnings:
    logger.warning("推敲チェック: %s", "; ".join(final_state.warnings))

  print(f"\n=== {final_state.draft.title} ===\n")
  print(final_state.draft.body_markdown)
  print(f"\nハッシュタグ: {' '.join('#' + h for h in final_state.draft.hashtags)}")
  print(f"文字数: {final_state.draft.char_count}")
