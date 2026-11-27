from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Every table class inherits from this, so SQLAlchemy can find all of them."""


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)  # lowercase; one row per player
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)  # short ID other tables point at
    url: Mapped[str] = mapped_column(unique=True)  # blocks duplicate games
    white_username: Mapped[str] = mapped_column(index=True)
    black_username: Mapped[str] = mapped_column(index=True)
    white_rating: Mapped[int]
    black_rating: Mapped[int]
    white_result: Mapped[str]  # "win", "resigned", "timeout", "checkmated"...
    black_result: Mapped[str]
    time_class: Mapped[str]  # "blitz", "rapid", "bullet", "daily"
    time_control: Mapped[str]  # "180+2"
    rated: Mapped[bool]
    eco_url: Mapped[str | None]  # some games have no opening link
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    pgn: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class HttpCache(Base):
    __tablename__ = "http_cache"

    url: Mapped[str] = mapped_column(
        primary_key=True
    )  # nothing points here, so URL is the key
    etag: Mapped[str]
    data: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
