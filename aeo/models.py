from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, Enum, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session

DATABASE_URL = "sqlite:///./aeo.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    domain = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)  # e.g. "CRM", "Project Management"

    citations = relationship("Citation", back_populates="brand")


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=False)

    queries = relationship("Query", back_populates="topic")


class Query(Base):
    """A question a user might ask an AI answer engine."""
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    intent = Column(Enum("informational", "commercial", "navigational", name="intent_type"))

    topic = relationship("Topic", back_populates="queries")
    runs = relationship("QueryRun", back_populates="query")


class AIEngine(Base):
    """An AI answer engine (ChatGPT, Perplexity, Claude, etc.)."""
    __tablename__ = "ai_engines"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    provider = Column(String, nullable=False)

    runs = relationship("QueryRun", back_populates="engine")


class QueryRun(Base):
    """One execution of a query against one AI engine at a specific time."""
    __tablename__ = "query_runs"
    id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=False)
    run_at = Column(DateTime, nullable=False, index=True)
    response_text = Column(Text)
    total_citations = Column(Integer, default=0)

    query = relationship("Query", back_populates="runs")
    engine = relationship("AIEngine", back_populates="runs")
    citations = relationship("Citation", back_populates="run")

    __table_args__ = (
        Index("ix_run_query_engine_date", "query_id", "engine_id", "run_at"),
    )


class Citation(Base):
    """A brand cited within a specific query run."""
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("query_runs.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    position = Column(Integer)           # 1 = first mentioned, 2 = second, etc.
    sentiment = Column(Enum("positive", "neutral", "negative", name="sentiment_type"))
    excerpt = Column(Text)               # snippet from the AI response mentioning the brand
    source_url = Column(String, nullable=True)  # page the engine cited; null when engine doesn't expose sources

    run = relationship("QueryRun", back_populates="citations")
    brand = relationship("Brand", back_populates="citations")

    __table_args__ = (
        Index("ix_citation_run_brand", "run_id", "brand_id"),
        Index("ix_citation_source_url", "source_url"),
    )


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return Session(engine)
