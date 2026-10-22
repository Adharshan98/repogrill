"""Database tables. SQLite by default (one file, nothing to install); set DATABASE_URL to use PostgreSQL."""
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text, create_engine, inspect, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./repogrill.db")

engine = create_engine(
    DATABASE_URL,
    # SQLite only allows the thread that opened it by default; FastAPI uses several threads
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RepoRow(Base):
    __tablename__ = "repos"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    url: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    chunks: Mapped[list["ChunkRow"]] = relationship(order_by="ChunkRow.position", cascade="all, delete-orphan")


class ChunkRow(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)  # order inside the repo, so topics can point at it
    file: Mapped[str] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(30))
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[bytes] = mapped_column(LargeBinary)  # 384 float32 numbers stored as raw bytes


class InterviewRow(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    topic_positions: Mapped[list[int]] = mapped_column(JSON)  # which chunks are the interview topics
    topic_number: Mapped[int] = mapped_column(Integer, default=0)
    follow_ups: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    study_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # saved so the LLM is asked only once

    repo: Mapped[RepoRow] = relationship()
    turns: Mapped[list["TurnRow"]] = relationship(order_by="TurnRow.position", cascade="all, delete-orphan")


class TurnRow(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(600))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    got_right: Mapped[str] = mapped_column(Text, default="")
    missed: Mapped[str] = mapped_column(Text, default="")
    ideal_answer: Mapped[str | None] = mapped_column(Text, nullable=True)


def init_db() -> None:
    """Create missing tables, then add any new optional columns to tables that already exist.

    This is a tiny migration step: when we add a nullable column (like `ideal_answer`), databases
    created by an older version get it automatically, without losing saved interviews.
    """
    Base.metadata.create_all(engine)
    existing = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            present = {c["name"] for c in existing.get_columns(table.name)}
            for column in table.columns:
                if column.name not in present and column.nullable:
                    column_type = column.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {column_type}'))
