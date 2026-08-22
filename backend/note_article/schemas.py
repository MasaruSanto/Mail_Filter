# note記事自動生成パイプラインで使うPydanticスキーマ定義

from typing import Literal, Optional

from pydantic import BaseModel, Field

SearchIntent = Literal["know", "do", "compare", "go"]


class ResearchSource(BaseModel):
  url: str
  title: str
  content: str = Field(..., description="検索結果の本文抜粋")
  published_at: Optional[str] = Field(default=None, description="情報源の公開日")


class SourceSummary(BaseModel):
  """1つの情報源に対するLLMの評価結果"""
  credibility_score: int = Field(..., ge=1, le=5, description="情報源の信頼度。一次情報・公式発表は5、個人ブログや出典不明は低め")
  summary: str = Field(..., description="日本語での要約")
  key_claims: list[str] = Field(default_factory=list, description="記事執筆で使える主張・数値")


class ResearchNote(BaseModel):
  source: ResearchSource
  credibility_score: int
  summary: str
  key_claims: list[str] = Field(default_factory=list)


class TitleCandidate(BaseModel):
  title: str
  length_score: float = 0.0
  keyword_score: float = 0.0
  hook_score: float = 0.0
  total_score: float = 0.0


class SeoDraftLLM(BaseModel):
  """SEO設計のLLM生出力（機械採点を適用する前）"""
  main_keyword: str
  sub_keywords: list[str] = Field(default_factory=list)
  search_intent: SearchIntent
  target_reader: str = Field(..., description="想定読者を一文で")
  hashtags: list[str] = Field(default_factory=list, description="note投稿用ハッシュタグ。#は付けない")
  title_candidates: list[str] = Field(..., description="タイトル候補")
  hook_scores: list[float] = Field(..., description="title_candidatesと同順のクリック誘引度自己採点(0-1)")


class SeoDesign(BaseModel):
  main_keyword: str
  sub_keywords: list[str] = Field(default_factory=list)
  search_intent: SearchIntent
  target_reader: str
  hashtags: list[str] = Field(default_factory=list)
  title_candidates: list[TitleCandidate] = Field(default_factory=list)
  chosen_title: str = ""


class OutlineSection(BaseModel):
  heading: str
  intent_note: str = Field(default="", description="このセクションが満たす検索意図")


class ArticleOutline(BaseModel):
  intro: str = Field(..., description="冒頭2〜3行のフック文")
  sections: list[OutlineSection]
  cta: str = Field(default="", description="末尾のフォロー・スキ導線")


class ArticleDraft(BaseModel):
  title: str
  body_markdown: str
  hashtags: list[str] = Field(default_factory=list)
  char_count: int = 0


class GraphState(BaseModel):
  """LangGraphのステート。各ノードがこれを読み書きしながらパイプラインを進める"""
  topic: str
  research_notes: list[ResearchNote] = Field(default_factory=list)
  seo: Optional[SeoDesign] = None
  outline: Optional[ArticleOutline] = None
  draft: Optional[ArticleDraft] = None
  errors: list[str] = Field(default_factory=list, description="処理継続不能な問題")
  warnings: list[str] = Field(default_factory=list, description="推敲チェックで見つかった改善点")
