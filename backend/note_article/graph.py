# リサーチ→SEO設計→構成→執筆→推敲のLangGraphパイプライン組み立て

from langgraph.graph import END, StateGraph

from note_article.nodes import NoteArticleNodes
from note_article.schemas import GraphState


def build_graph(provider: str = "claude", api_key: str | None = None,
                 model_name: str | None = None):
  nodes = NoteArticleNodes(provider=provider, api_key=api_key, model_name=model_name)

  graph = StateGraph(GraphState)
  graph.add_node("research", nodes.research)
  graph.add_node("seo_design", nodes.seo_design)
  graph.add_node("outline", nodes.outline)
  graph.add_node("draft", nodes.draft)
  graph.add_node("review", nodes.review)

  graph.set_entry_point("research")
  graph.add_edge("research", "seo_design")
  graph.add_edge("seo_design", "outline")
  graph.add_edge("outline", "draft")
  graph.add_edge("draft", "review")
  graph.add_edge("review", END)

  return graph.compile()
