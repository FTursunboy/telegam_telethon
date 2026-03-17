from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from telethon.tl.custom.message import Message
from telethon.tl import functions

from telegram_api_server.core.config import get_settings
from telegram_api_server.db.session import SessionLocal
from telegram_api_server.models.telegram_account import TelegramAccount
from telegram_api_server.services.update_mapper import UpdateMapper
from telegram_api_server.services.webhook_dispatcher import webhook_dispatcher

logger = logging.getLogger(__name__)


@dataclass
class LoginState:
    phone: str
    phone_code_hash: str


class SessionManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.clients: dict[str, TelegramClient] = {}
        self.login_state: dict[str, LoginState] = {}
        self.update_mapper = UpdateMapper()

        self._handlers_attached: set[str] = set()
        self._entity_cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
        self._dedup_cache: dict[str, float] = {}
        self._pending_by_session: dict[str, int] = {}
        self._bg_tasks: set[asyncio.Task[Any]] = set()

        Path(self.settings.telethon_session_dir).mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_name: str) -> str:
        return os.path.join(self.settings.telethon_session_dir, session_name)

    async def _get_or_create_client(self, session_name: str, api_id: int, api_hash: str) -> TelegramClient:
        client = self.clients.get(session_name)
        if client:
            if not client.is_connected():
                await client.connect()
            return client

        client = TelegramClient(self._session_path(session_name), api_id=api_id, api_hash=api_hash)
        await client.connect()
        self.clients[session_name] = client
        self._attach_update_handlers(session_name, client)
        return client

    def _attach_update_handlers(self, session_name: str, client: TelegramClient) -> None:
        if session_name in self._handlers_attached:
            return

        @client.on(events.NewMessage)
        async def _on_new_message(event: events.NewMessage.Event) -> None:
            await self._handle_update_event(session_name, "updateNewMessage", event.message)

        @client.on(events.MessageEdited)
        async def _on_message_edited(event: events.MessageEdited.Event) -> None:
            await self._handle_update_event(session_name, "updateEditMessage", event.message)

        self._handlers_attached.add(session_name)

    async def _handle_update_event(self, session_name: str, update_type: str, message: Message) -> None:
        if not message or not message.is_private:
            return

        account_data = await self._get_account_data(session_name)
        if not account_data:
            return

        webhook_url = account_data.get("webhook_url")
        if not webhook_url:
            return

        self_user_id = account_data.get("telegram_user_id")

        chat = await self._resolve_chat_info(session_name, message, self_user_id)
        payload = self.update_mapper.map_message(
            session_name=session_name,
            update_type=update_type,
            message=message,
            chat=chat,
            self_user_id=self_user_id,
        )

        if self._is_duplicate(payload):
            return

        pending = self._pending_by_session.get(session_name, 0)
        if pending >= self.settings.webhook_max_pending_per_session:
            logger.warning("Webhook backpressure limit reached", extra={"session_name": session_name})
            return

        self._pending_by_session[session_name] = pending + 1
        task = asyncio.create_task(self._dispatch_webhook_task(session_name, webhook_url, payload, message))
        self._bg_tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task[Any]) -> None:
        self._bg_tasks.discard(task)
        try:
            task.result()
        except Exception as exc:  # noqa: BLE001
            logger.error("Webhook background task failed", exc_info=exc)

    async def _dispatch_webhook_task(
        self,
        session_name: str,
        webhook_url: str,
        payload: dict[str, Any],
        message: Message,
    ) -> None:
        file_content: bytes | None = None
        file_name: str | None = None

        try:
            if payload.get("media"):
                file_content = await self._download_media_content(session_name, message)
                if file_content:
                    file_name = self._resolve_media_filename(payload)
            await webhook_dispatcher.dispatch(
                webhook_url=webhook_url,
                payload=payload,
                file_content=file_content,
                file_name=file_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Webhook dispatch failed",
                extra={"session_name": session_name, "message_id": payload.get("message_id")},
                exc_info=exc,
            )
        finally:
            current = self._pending_by_session.get(session_name, 1)
            self._pending_by_session[session_name] = max(0, current - 1)

    async def _download_media_content(self, session_name: str, message: Message) -> bytes | None:
        client = self.clients.get(session_name)
        if not client:
            return None
        try:
            data = await client.download_media(message, file=bytes)
            if isinstance(data, bytes):
                return data
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to download Telegram media", extra={"session_name": session_name}, exc_info=exc)
            return None

    @staticmethod
    def _resolve_media_filename(payload: dict[str, Any]) -> str:
        media = payload.get("media") or {}
        if media.get("file_name"):
            return str(media["file_name"])
        if media.get("has_photo"):
            return f"photo_{payload.get('message_id')}.jpg"
        mime_type = media.get("mime_type")
        if isinstance(mime_type, str) and "/" in mime_type:
            ext = mime_type.split("/", maxsplit=1)[1]
            return f"file_{payload.get('message_id')}.{ext}"
        return f"file_{payload.get('message_id')}.bin"

    def _is_duplicate(self, payload: dict[str, Any]) -> bool:
        now = time.time()
        key = f"{payload.get('session')}:{payload.get('message_id')}:{payload.get('update_type')}"
        expires_at = self._dedup_cache.get(key)
        if expires_at and expires_at > now:
            return True

        self._dedup_cache[key] = now + self.settings.webhook_dedup_ttl_seconds

        if len(self._dedup_cache) > 5000:
            self._dedup_cache = {k: v for k, v in self._dedup_cache.items() if v > now}
        return False

    async def _get_account_data(self, session_name: str) -> dict[str, Any] | None:
        async with SessionLocal() as db:
            result = await db.execute(
                select(TelegramAccount.webhook_url, TelegramAccount.telegram_user_id).where(
                    TelegramAccount.session_name == session_name
                )
            )
            row = result.first()
            if not row:
                return None
            webhook_url, telegram_user_id = row
            return {
                "webhook_url": webhook_url,
                "telegram_user_id": int(telegram_user_id) if telegram_user_id and str(telegram_user_id).isdigit() else None,
            }

    async def _resolve_chat_info(
        self,
        session_name: str,
        message: Message,
        self_user_id: int | None,
    ) -> dict[str, Any]:
        from_id = self.update_mapper._extract_user_id(message.from_id)
        peer_id = self.update_mapper._extract_user_id(message.peer_id)

        target_user_id = peer_id if bool(message.out) else from_id
        if target_user_id is None and self_user_id:
            target_user_id = self_user_id

        if target_user_id is None:
            return {"first_name": None, "username": None, "id": None, "phone_number": None}

        cache_key = (session_name, target_user_id)
        cached = self._entity_cache.get(cache_key)
        now = time.time()
        if cached and cached[0] > now:
            return cached[1]

        client = self.clients.get(session_name)
        if not client:
            return {"first_name": None, "username": None, "id": target_user_id, "phone_number": None}

        try:
            entity = await client.get_entity(target_user_id)
            chat = {
                "first_name": getattr(entity, "first_name", None),
                "username": getattr(entity, "username", None),
                "id": getattr(entity, "id", target_user_id),
                "phone_number": getattr(entity, "phone", None),
            }
        except Exception:  # noqa: BLE001
            chat = {"first_name": None, "username": None, "id": target_user_id, "phone_number": None}

        self._entity_cache[cache_key] = (now + self.settings.entity_cache_ttl_seconds, chat)
        return chat

    async def start_user_login(
        self,
        session_name: str,
        api_id: int,
        api_hash: str,
        phone: str,
        *,
        force_sms: bool = False,
    ) -> dict[str, Any]:
        client = await self._get_or_create_client(session_name, api_id, api_hash)
        state = self.login_state.get(session_name)
        if force_sms and state and state.phone_code_hash:
            code = await client(
                functions.auth.ResendCodeRequest(phone_number=state.phone, phone_code_hash=state.phone_code_hash)
            )
        else:
            code = await client.send_code_request(phone, force_sms=force_sms)

        new_hash = code.phone_code_hash if getattr(code, "phone_code_hash", None) else (state.phone_code_hash if state else None)
        if not new_hash:
            raise ValueError("Telegram did not return phone_code_hash")

        self.login_state[session_name] = LoginState(phone=phone, phone_code_hash=new_hash)
        return {
            "status": "waiting_code",
            "needs_code": True,
            "needs_2fa": False,
            "session_name": session_name,
            "sent_code_type": code.type.__class__.__name__ if getattr(code, "type", None) else None,
            "next_code_type": code.next_type.__class__.__name__ if getattr(code, "next_type", None) else None,
            "timeout": getattr(code, "timeout", None),
            "error": None,
        }

    async def complete_code(self, session_name: str, code: str) -> dict[str, Any]:
        state = self.login_state.get(session_name)
        if not state:
            raise ValueError("Login state not found. Start login first")

        client = self.clients[session_name]
        try:
            user = await client.sign_in(phone=state.phone, code=code, phone_code_hash=state.phone_code_hash)
            self.login_state.pop(session_name, None)
            return {
                "status": "ready",
                "needs_2fa": False,
                "session_name": session_name,
                "user_data": {
                    "id": getattr(user, "id", None),
                    "username": getattr(user, "username", None),
                    "first_name": getattr(user, "first_name", None),
                    "phone": getattr(user, "phone", None),
                },
                "error": None,
            }
        except SessionPasswordNeededError:
            return {
                "status": "waiting_2fa",
                "needs_2fa": True,
                "session_name": session_name,
                "error": None,
            }

    async def complete_2fa(self, session_name: str, password: str) -> dict[str, Any]:
        client = self.clients.get(session_name)
        if not client:
            raise ValueError("Session is not initialized")
        user = await client.sign_in(password=password)
        self.login_state.pop(session_name, None)
        return {
            "status": "ready",
            "session_name": session_name,
            "user_data": {
                "id": getattr(user, "id", None),
                "username": getattr(user, "username", None),
                "first_name": getattr(user, "first_name", None),
            },
            "error": None,
        }

    async def start_bot(self, session_name: str, api_id: int, api_hash: str, bot_token: str) -> dict[str, Any]:
        client = await self._get_or_create_client(session_name, api_id, api_hash)
        await client.start(bot_token=bot_token)
        me = await client.get_me()
        return {
            "status": "ready",
            "needs_code": False,
            "needs_2fa": False,
            "session_name": session_name,
            "bot_data": {
                "id": getattr(me, "id", None),
                "username": getattr(me, "username", None),
                "first_name": getattr(me, "first_name", None),
            },
            "error": None,
        }

    async def stop(self, session_name: str) -> dict[str, Any]:
        client = self.clients.pop(session_name, None)
        self.login_state.pop(session_name, None)
        self._handlers_attached.discard(session_name)
        self._pending_by_session.pop(session_name, None)
        if client:
            await client.disconnect()
        return {"status": "stopped", "error": None}

    async def restart(
        self,
        session_name: str,
        api_id: int,
        api_hash: str,
        account_type: str,
        phone: str | None,
        bot_token: str | None,
    ) -> dict[str, Any]:
        await self.stop(session_name)
        if account_type == "bot":
            if not bot_token:
                raise ValueError("bot_token is required")
            return await self.start_bot(session_name, api_id, api_hash, bot_token)
        if not phone:
            raise ValueError("phone is required")
        return await self.start_user_login(session_name, api_id, api_hash, phone)

    @staticmethod
    def _normalize_parse_mode(parse_mode: str | None, *, default_markdown: bool = False) -> str | None:
        if parse_mode is None:
            return "md" if default_markdown else None
        if parse_mode == "Markdown":
            return "md"
        if parse_mode == "HTML":
            return "html"
        return parse_mode

    @staticmethod
    def _extract_peer_id(peer: Any) -> int | None:
        if peer is None:
            return None
        for attr in ("user_id", "chat_id", "channel_id"):
            value = getattr(peer, attr, None)
            if value is not None:
                return int(value)
        if isinstance(peer, int):
            return peer
        return None

    async def send_message(
        self,
        session_name: str,
        peer: str,
        message: str,
        parse_mode: str | None,
        reply_to_message_id: int | None,
    ) -> dict[str, Any]:
        client = self.clients.get(session_name)
        if not client:
            raise ValueError("Session not active")
        parse = self._normalize_parse_mode(parse_mode, default_markdown=True)
        sent = await client.send_message(entity=peer, message=message, parse_mode=parse, reply_to=reply_to_message_id)
        sent_date = int(sent.date.timestamp()) if sent.date else None
        peer_id = self._extract_peer_id(sent.peer_id)
        return {
            "success": True,
            "message_id": sent.id,
            "date": sent_date,
            "peer_id": peer_id,
            "response": {"response": {"id": sent.id, "date": sent_date, "peer_id": peer_id}},
        }

    async def send_file(
        self,
        session_name: str,
        peer: str,
        file_path: str,
        caption: str | None,
        parse_mode: str | None,
        voice_note: bool = False,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        client = self.clients.get(session_name)
        if not client:
            raise ValueError("Session not active")
        parse = self._normalize_parse_mode(parse_mode)
        sent = await client.send_file(
            entity=peer,
            file=file_path,
            caption=caption,
            parse_mode=parse,
            voice_note=voice_note,
            reply_to=reply_to_message_id,
        )
        sent_date = int(sent.date.timestamp()) if sent.date else None
        return {
            "success": True,
            "message_id": sent.id,
            "date": sent_date,
            "response": {"response": {"id": sent.id, "date": sent_date}},
        }

    async def edit_message(
        self,
        session_name: str,
        peer: str,
        message_id: int,
        message: str,
        parse_mode: str | None,
    ) -> dict[str, Any]:
        client = self.clients.get(session_name)
        if not client:
            raise ValueError("Session not active")
        parse = self._normalize_parse_mode(parse_mode)
        edited = await client.edit_message(entity=peer, message=message_id, text=message, parse_mode=parse)
        edited_date = int(edited.date.timestamp()) if edited.date else None
        return {
            "success": True,
            "message_id": edited.id,
            "date": edited_date,
            "response": {"response": {"id": edited.id, "date": edited_date}},
        }

    async def react_message(
        self,
        session_name: str,
        peer: str,
        message_id: int,
        reaction: str | None,
        remove: bool,
    ) -> dict[str, Any]:
        client = self.clients.get(session_name)
        if not client:
            raise ValueError("Session not active")
        await client.send_reaction(entity=peer, message=message_id, reaction=[] if remove else [reaction or "👍"])
        return {"success": True, "response": {"ok": True}}

    def is_active(self, session_name: str) -> bool:
        return session_name in self.clients

    def compatibility_runtime(self, session_name: str) -> dict[str, Any]:
        suffix = abs(hash(session_name)) % 10000
        return {
            "has_container": self.is_active(session_name),
            "container_name": f"py_runtime_{session_name}",
            "container_port": 30000 + suffix,
            "runtime_session_claimed_at": datetime.now(timezone.utc),
        }


session_manager = SessionManager()
