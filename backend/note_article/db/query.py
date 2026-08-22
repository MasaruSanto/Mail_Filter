# note記事パイプラインのDB保存・参照関数

import json

from sqlalchemy.orm import Session

from note_article.db.engine import Article, Performance, ResearchNoteRecord, Topic
from note_article.schemas import GraphState


def save_pipeline_result(db: Session, state: GraphState) -> Article | None:
  """パイプライン実行結果（トピック・リサーチノート・記事）をまとめて保存する"""
  topic = Topic(
    keyword_main=state.seo.main_keyword if state.seo else state.topic,
    keywords_sub=json.dumps(state.seo.sub_keywords, ensure_ascii=False) if state.seo else None,
    search_intent=state.seo.search_intent if state.seo else None,
    status="drafted" if state.draft else "researching",
  )
  db.add(topic)
  db.flush()

  for note in state.research_notes:
    db.add(ResearchNoteRecord(
      topic_id=topic.id,
      source_url=note.source.url,
      source_title=note.source.title,
      published_at=note.source.published_at,
      credibility_score=note.credibility_score,
      summary=note.summary,
      key_claims=json.dumps(note.key_claims, ensure_ascii=False),
    ))

  if not state.draft:
    db.commit()
    return None

  title_score = None
  if state.seo:
    title_score = next(
      (c.total_score for c in state.seo.title_candidates if c.title == state.draft.title),
      None,
    )

  article = Article(
    topic_id=topic.id,
    title=state.draft.title,
    title_score=title_score,
    outline=state.outline.model_dump_json() if state.outline else None,
    body_markdown=state.draft.body_markdown,
    hashtags=json.dumps(state.draft.hashtags, ensure_ascii=False),
    intro_text=state.outline.intro if state.outline else None,
    char_count=state.draft.char_count,
    status="draft",
  )
  db.add(article)
  db.commit()
  db.refresh(article)
  return article


def save_performance(db: Session, article_id: str, pv: int | None = None, likes: int | None = None,
                      comments: int | None = None, follows_gained: int | None = None) -> Performance:
  """投稿後のPV・スキ数などを記録し、次回のタイトル・構成生成にフィードバックできるようにする"""
  perf = Performance(article_id=article_id, pv=pv, likes=likes, comments=comments,
                     follows_gained=follows_gained)
  db.add(perf)
  db.commit()
  db.refresh(perf)
  return perf


def get_top_titles(db: Session, limit: int = 10) -> list[Article]:
  """スキ数の多い記事を新しい順に取得する（次回のタイトル生成プロンプトへの参考例として使う）"""
  return (
    db.query(Article)
    .join(Performance, Performance.article_id == Article.id)
    .order_by(Performance.likes.desc())
    .limit(limit)
    .all()
  )
