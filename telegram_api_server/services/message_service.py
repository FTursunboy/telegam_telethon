from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api_server.core.errors import BusinessError
from telegram_api_server.models.telegram_account import TelegramAccount
from telegram_api_server.runtime.session_manager import session_manager
from telegram_api_server.services.file_fetcher import download_to_tmp


class MessageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _account(self, session_name: str) -> TelegramAccount:
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if not account:
            raise BusinessError("Session not found", status_code=500)
        if account.status != "ready":
            raise BusinessError(f"Account #{account.id} is not ready (status: {account.status})")
        return account

    async def send_message(
        self,
        session_name: str,
        peer: str,
        message: str,
        parse_mode: str | None,
        reply_to_message_id: int | None,
    ) -> dict:
        account = await self._account(session_name)
        result = await session_manager.send_message(session_name, peer, message, parse_mode or "Markdown", reply_to_message_id)
        account.messages_sent_count += 1
        account.last_activity_at = datetime.now(timezone.utc)
        await self.db.commit()
        return result

    async def send_voice(
        self,
        session_name: str,
        peer: str,
        voice_url: str,
        caption: str | None,
        reply_to_message_id: int | None,
    ) -> dict:
        account = await self._account(session_name)
        path = await download_to_tmp(voice_url, session_name)
        try:
            result = await session_manager.send_file(
                session_name,
                peer,
                path,
                caption,
                parse_mode=None,
                voice_note=True,
                reply_to_message_id=reply_to_message_id,
            )
        finally:
            Path(path).unlink(missing_ok=True)
        account.messages_sent_count += 1
        account.last_activity_at = datetime.now(timezone.utc)
        await self.db.commit()
        return result

    async def send_file(
        self,
        session_name: str,
        peer: str,
        file_url: str,
        caption: str | None,
        parse_mode: str | None,
        reply_to_message_id: int | None,
    ) -> dict:
        account = await self._account(session_name)
        path = await download_to_tmp(file_url, session_name)
        try:
            result = await session_manager.send_file(
                session_name,
                peer,
                path,
                caption,
                parse_mode,
                voice_note=False,
                reply_to_message_id=reply_to_message_id,
            )
        finally:
            Path(path).unlink(missing_ok=True)
        account.messages_sent_count += 1
        account.last_activity_at = datetime.now(timezone.utc)
        await self.db.commit()
        return result

    async def react_message(
        self,
        session_name: str,
        peer: str,
        message_id: int,
        reaction: str | None,
        remove: bool,
    ) -> dict:
        await self._account(session_name)
        return await session_manager.react_message(session_name, peer, message_id, reaction, remove)

    async def edit_message(
        self,
        session_name: str,
        peer: str,
        message_id: int,
        message: str,
        parse_mode: str | None,
    ) -> dict:
        await self._account(session_name)
        return await session_manager.edit_message(session_name, peer, message_id, message, parse_mode)
