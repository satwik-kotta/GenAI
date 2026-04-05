from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["SessionToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    plans: Mapped[list["PlanHistory"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class PlanHistory(Base):
    __tablename__ = "plan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user_input: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(255))
    decision: Mapped[str] = mapped_column(String(255))
    weather: Mapped[str] = mapped_column(String(64))
    start_time: Mapped[str] = mapped_column(String(64))
    end_time: Mapped[str] = mapped_column(String(64))
    selected_place_name: Mapped[str] = mapped_column(String(255))
    selected_place_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    selected_place_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    calendar_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="plans")
