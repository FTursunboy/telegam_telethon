from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telegram_api_server.db.base import Base


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_app_id: Mapped[int] = mapped_column(ForeignKey("telegram_apps.id"), index=True)

    type: Mapped[str] = mapped_column(String(32), default="user")
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bot_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    webhook_url: Mapped[str] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(64), default="creating")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    telegram_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    messages_sent_count: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runtime_node: Mapped[str | None] = mapped_column(String(255), nullable=True)
    runtime_pid: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    runtime_session_claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    telegram_app = relationship("TelegramApp", back_populates="accounts")
