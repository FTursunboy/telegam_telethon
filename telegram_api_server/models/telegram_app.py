from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from telegram_api_server.db.base import Base


class TelegramApp(Base):
    __tablename__ = "telegram_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant: Mapped[str] = mapped_column(String(255), default="default")
    name: Mapped[str] = mapped_column(String(255))
    api_id: Mapped[str] = mapped_column(String(255), index=True)
    api_hash_encrypted: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    accounts = relationship("TelegramAccount", back_populates="telegram_app")
