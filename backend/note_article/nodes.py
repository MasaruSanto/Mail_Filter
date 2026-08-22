# LangGraphの各ノード処理

import logging

from note_article.schemas import (
  ArticleDraft,
  ArticleOutline,
  GraphState,
  ResearchNote,
  ResearchSource,
  SeoDesign,
  SeoDraftLLM,
  SourceSummary,
  TitleCandidate,
)
from note_article.llm import get_chat_model, with_structured
from note_article.review import check_heading_keywords, check_intro_hook, check_length
from note_article.search import WebSearchClient
from note_article.seo_scoring import score_title

logger = logging.getLogger(__name__)

_RESEARCH_PROMPT = """
以下はWeb検索で見つかった情報源です。トピック「{topic}」の記事執筆のためにリサーチしています。

タイトル: {title}
URL: {url}
本文抜粋: {content}

この情報源の信頼度(1-5、公式発表や一次情報は5、個人ブログや出典不明な内容は低め)を判定し、
日本語で要約し、記事で使えそうな主張・数値をkey_claimsとして抽出してください。
"""

_SEO_PROMPT = """
トピック「{topic}」についてnote記事を書きます。以下はリサーチ結果の要約です。

{research_summary}

これを踏まえて以下を日本語で設計してください。
- main_keyword: 記事のメインキーワード1つ
- sub_keywords: サブキーワード2〜4個
- search_intent: know(知りたい) / do(やり方が知りたい) / compare(比較検討) / go(固有名詞検索) のいずれか
- target_reader: 想定読者を一文で
- hashtags: note投稿用ハッシュタグを最大5個（#は付けない）。多くの人が見る一般的な語(大タグ)と、埋もれにくい具体的な語(中規模タグ)を組み合わせること
- title_candidates: タイトル候補を6本。メインキーワードを前方(できれば冒頭15文字以内)に含め、32文字前後を目安にすること
- hook_scores: title_candidatesと同じ順序で、クリックしたくなる度合いを0〜1で自己採点すること(具体性・数字・ベネフィットの明示を評価基準にする)
"""

_OUTLINE_PROMPT = """
トピック「{topic}」、メインキーワード「{main_keyword}」、想定読者「{target_reader}」でnote記事の構成案を作ります。
検索意図: {search_intent}
サブキーワード: {sub_keywords}

リサーチ要約:
{research_summary}

以下を日本語で作成してください。
- intro: 記事冒頭の2〜3行のフック文。誰向けの記事で何が得られるかを明示し、noteのフィード上のプレビューで離脱されないようにすること
- sections: 大見出しのリスト。各見出しにサブキーワードを分散させ、その見出しが検索意図のどの部分を満たすか(intent_note)も書くこと。悩み提起→共感→解決の流れを意識すること
- cta: 記事末尾でフォロー・スキを促す一文
"""

_DRAFT_PROMPT = """
以下の構成案に沿って、note記事の本文をMarkdown形式で執筆してください。

タイトル: {title}
導入: {intro}
見出し構成:
{sections}

リサーチで得られた事実は以下の通りです。本文中で使う主張は必ずこのリサーチ結果に基づき、
憶測や未確認の情報を断定的に書かないでください。

{research_summary}

条件:
- 全体で2000〜4000字程度
- 見出しは「## 見出し」のMarkdown形式で、構成案の見出しをそのまま使うこと
- 冒頭は導入文をベースに書き出すこと
- 箇条書きを適度に使い、一文を長くしすぎないこと
- 末尾に「{cta}」を含めること
"""


class NoteArticleNodes:
  """LangGraphの各ノード処理。1インスタンスが1回のパイプライン実行を担当する"""

  def __init__(self, provider: str = "claude", api_key: str | None = None,
               model_name: str | None = None, search_client: WebSearchClient | None = None):
    self._provider = provider
    self._llm = get_chat_model(provider=provider, api_key=api_key, model_name=model_name)
    self._search = search_client or WebSearchClient()

  def research(self, state: GraphState) -> GraphState:
    try:
      results = self._search.search(state.topic)
    except RuntimeError as e:
      state.errors.append(str(e))
      return state

    if not results:
      state.errors.append("検索結果が0件でした")
      return state

    structured = with_structured(self._llm, self._provider, SourceSummary)
    for r in results:
      try:
        summary: SourceSummary = structured.invoke(_RESEARCH_PROMPT.format(
          topic=state.topic, title=r["title"], url=r["url"], content=r["content"][:2000],
        ))
        state.research_notes.append(ResearchNote(
          source=ResearchSource(
            url=r["url"], title=r["title"], content=r["content"][:2000],
            published_at=r.get("published_at"),
          ),
          credibility_score=summary.credibility_score,
          summary=summary.summary,
          key_claims=summary.key_claims,
        ))
      except Exception as e:
        logger.warning("情報源の要約に失敗、スキップ (%s): %s", r.get("url"), e)

    if not state.research_notes:
      state.errors.append("リサーチノートを1件も作成できませんでした")
    return state

  def seo_design(self, state: GraphState) -> GraphState:
    if not state.research_notes:
      state.errors.append("リサーチ結果がないためSEO設計をスキップしました")
      return state

    research_summary = self._format_research_summary(state.research_notes)
    structured = with_structured(self._llm, self._provider, SeoDraftLLM)
    raw: SeoDraftLLM = structured.invoke(_SEO_PROMPT.format(
      topic=state.topic, research_summary=research_summary,
    ))

    competitor_titles = [n.source.title for n in state.research_notes if n.source.title]
    candidates = []
    for title, hook in zip(raw.title_candidates, raw.hook_scores):
      scores = score_title(title, raw.main_keyword, competitor_titles, hook_score=hook)
      candidates.append(TitleCandidate(
        title=title,
        length_score=scores["length_score"],
        keyword_score=scores["keyword_score"],
        hook_score=scores["hook_score"],
        total_score=scores["total_score"],
      ))
    candidates.sort(key=lambda c: c.total_score, reverse=True)

    state.seo = SeoDesign(
      main_keyword=raw.main_keyword,
      sub_keywords=raw.sub_keywords,
      search_intent=raw.search_intent,
      target_reader=raw.target_reader,
      hashtags=raw.hashtags[:5],
      title_candidates=candidates,
      chosen_title=candidates[0].title if candidates else "",
    )
    return state

  def outline(self, state: GraphState) -> GraphState:
    if not state.seo:
      state.errors.append("SEO設計がないため構成案生成をスキップしました")
      return state

    research_summary = self._format_research_summary(state.research_notes)
    structured = with_structured(self._llm, self._provider, ArticleOutline)
    state.outline = structured.invoke(_OUTLINE_PROMPT.format(
      topic=state.topic,
      main_keyword=state.seo.main_keyword,
      target_reader=state.seo.target_reader,
      search_intent=state.seo.search_intent,
      sub_keywords="、".join(state.seo.sub_keywords),
      research_summary=research_summary,
    ))
    return state

  def draft(self, state: GraphState) -> GraphState:
    if not state.outline or not state.seo:
      state.errors.append("構成案がないため執筆をスキップしました")
      return state

    research_summary = self._format_research_summary(state.research_notes)
    sections_text = "\n".join(
      f"- {s.heading}（{s.intent_note}）" for s in state.outline.sections
    )
    response = self._llm.invoke(_DRAFT_PROMPT.format(
      title=state.seo.chosen_title,
      intro=state.outline.intro,
      sections=sections_text,
      research_summary=research_summary,
      cta=state.outline.cta,
    ))
    body = response.content if hasattr(response, "content") else str(response)

    state.draft = ArticleDraft(
      title=state.seo.chosen_title,
      body_markdown=body,
      hashtags=state.seo.hashtags,
      char_count=len(body),
    )
    return state

  def review(self, state: GraphState) -> GraphState:
    if not state.draft or not state.seo:
      return state

    checks = [check_length(state.draft.body_markdown)]
    if state.outline:
      checks.append(check_intro_hook(state.outline.intro, state.seo.main_keyword))
      checks.append(check_heading_keywords(state.outline.sections, state.seo.sub_keywords))

    state.warnings.extend(c for c in checks if c)
    return state

  @staticmethod
  def _format_research_summary(notes: list[ResearchNote]) -> str:
    lines = []
    for n in notes:
      claims = "、".join(n.key_claims) if n.key_claims else "(主張なし)"
      lines.append(f"- [{n.source.title}]({n.source.url}) 信頼度{n.credibility_score}/5: {n.summary} / 主張: {claims}")
    return "\n".join(lines)
