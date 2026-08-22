# note記事パイプライン用DB（トピック・リサーチノート・記事・パフォーマンス）

import os
import uuid
from datetime import datetime

from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, String,
                        Text, create_engine, event)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'note_article.db'))
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
  DATABASE_URL,
  echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
  connect_args={
    "check_same_thread": False,
    "timeout": 30,
  },
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
  cursor = dbapi_conn.cursor()
  cursor.execute("PRAGMA journal_mode=WAL")
  cursor.execute("PRAGMA synchronous=NORMAL")
  cursor.execute("PRAGMA foreign_keys=ON")
  cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


class Topic(Base):
  __tablename__ = "topics"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  keyword_main = Column(Text, nullable=False)
  keywords_sub = Column(Text, nullable=True, comment="JSON文字列のリスト")
  search_intent = Column(String(20), nullable=True)
  priority_score = Column(Float, nullable=True)
  status = Column(String(20), nullable=False, default="researching", comment="researching|drafted|published")
  created_at = Column(DateTime, default=datetime.now, nullable=False)


class ResearchNoteRecord(Base):
  __tablename__ = "research_notes"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
  source_url = Column(Text, nullable=False)
  source_title = Column(Text, nullable=True)
  published_at = Column(Text, nullable=True)
  credibility_score = Column(Integer, nullable=True)
  summary = Column(Text, nullable=True)
  key_claims = Column(Text, nullable=True, comment="JSON文字列のリスト")
  fetched_at = Column(DateTime, default=datetime.now, nullable=False)
  topic = relationship("Topic", backref="research_notes")


class Article(Base):
  __tablename__ = "articles"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  topic_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True)
  title = Column(Text, nullable=False)
  title_score = Column(Float, nullable=True)
  outline = Column(Text, nullable=True, comment="JSON文字列")
  body_markdown = Column(Text, nullable=False)
  hashtags = Column(Text, nullable=True, comment="JSON文字列のリスト")
  intro_text = Column(Text, nullable=True)
  char_count = Column(Integer, nullable=True)
  status = Column(String(20), nullable=False, default="draft", comment="draft|reviewed|published")
  created_at = Column(DateTime, default=datetime.now, nullable=False)
  published_at = Column(DateTime, nullable=True)
  topic = relationship("Topic", backref="articles")


class ArticleSource(Base):
  __tablename__ = "article_sources"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
  research_note_id = Column(String(36), ForeignKey("research_notes.id", ondelete="SET NULL"), nullable=True)
  claim_text = Column(Text, nullable=False, comment="本文中の主張。出典と突き合わせるためのハルシネーション対策")


class Performance(Base):
  __tablename__ = "performance"
  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  article_id = Column(String(36), ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True)
  pv = Column(Integer, nullable=True)
  likes = Column(Integer, nullable=True)
  comments = Column(Integer, nullable=True)
  follows_gained = Column(Integer, nullable=True)
  measured_at = Column(DateTime, default=datetime.now, nullable=False)


def create_tables():
  Base.metadata.create_all(engine)


if __name__ == "__main__":
  create_tables()
