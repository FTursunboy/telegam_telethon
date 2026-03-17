from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api_server.core.errors import BusinessError
from telegram_api_server.models.telegram_account import TelegramAccount
from telegram_api_server.models.telegram_app import TelegramApp
from telegram_api_server.runtime.session_manager import session_manager
from telegram_api_server.utils.crypto import decrypt_text, encrypt_text


class AccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _find_or_create_app(self, api_id: str, api_hash: str) -> TelegramApp:
        result = await self.db.execute(select(TelegramApp).where(TelegramApp.api_id == api_id))
        app = result.scalar_one_or_none()
        if app:
            app.api_hash_encrypted = encrypt_text(api_hash) or ""
            await self.db.flush()
            return app

        app = TelegramApp(
            tenant="default",
            name=f"App {api_id}",
            api_id=api_id,
            api_hash_encrypted=encrypt_text(api_hash) or "",
            status="active",
        )
        self.db.add(app)
        await self.db.flush()
        return app

    async def _find_or_create_account(self, app_id: int, data: dict) -> TelegramAccount:
        session_name = data.get("session_name") or f"session_{uuid4().hex[:10]}"
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if account:
            account.webhook_url = str(data["webhook_url"])
            if data.get("phone"):
                account.phone = data["phone"]
            if data.get("bot_token"):
                account.bot_token_encrypted = encrypt_text(data["bot_token"])
            await self.db.flush()
            return account

        account = TelegramAccount(
            telegram_app_id=app_id,
            type=data["type"],
            phone=data.get("phone"),
            bot_token_encrypted=encrypt_text(data.get("bot_token")),
            session_name=session_name,
            webhook_url=str(data["webhook_url"]),
            status="creating",
        )
        self.db.add(account)
        await self.db.flush()
        return account

    async def start_login(self, data: dict) -> dict:
        app = await self._find_or_create_app(data["api_id"], data["api_hash"])
        account = await self._find_or_create_account(app.id, data)

        if data["type"] == "user":
            if not data.get("phone"):
                raise BusinessError("phone is required for user")

            # If client repeats login/start for an existing waiting_code session,
            # request SMS fallback from Telegram.
            force_sms = account.status == "waiting_code" and not bool(data.get("force_recreate"))
            result = await session_manager.start_user_login(
                account.session_name,
                int(app.api_id),
                data["api_hash"],
                data["phone"],
                force_sms=force_sms,
            )
            account.status = "waiting_code"
        else:
            bot_token = data.get("bot_token")
            if not bot_token:
                raise BusinessError("bot_token is required for bot")
            result = await session_manager.start_bot(account.session_name, int(app.api_id), data["api_hash"], bot_token)
            account.status = "ready"
            result_bot_data = result.get("bot_data", {})
            account.telegram_user_id = str(result_bot_data.get("id")) if result_bot_data.get("id") else None
            account.telegram_username = result_bot_data.get("username")
            account.first_name = result_bot_data.get("first_name")
            account.authorized_at = datetime.now(timezone.utc)

        account.last_error = None
        await self.db.commit()
        return result

    async def complete_code(self, session_name: str, code: str) -> dict:
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if not account:
            raise BusinessError("Session not found", status_code=500)

        if account.status != "waiting_code":
            raise BusinessError("Account is not waiting for code")

        payload = await session_manager.complete_code(session_name, code)
        account.status = payload["status"]

        user_data = payload.get("user_data", {})
        if payload["status"] == "ready":
            account.telegram_user_id = str(user_data.get("id")) if user_data.get("id") else None
            account.telegram_username = user_data.get("username")
            account.first_name = user_data.get("first_name")
            account.authorized_at = datetime.now(timezone.utc)

        await self.db.commit()
        return payload

    async def complete_2fa(self, session_name: str, password: str) -> dict:
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if not account:
            raise BusinessError("Session not found", status_code=500)

        if account.status != "waiting_2fa":
            raise BusinessError("Account is not waiting for 2FA")

        payload = await session_manager.complete_2fa(session_name, password)
        account.status = "ready"
        user_data = payload.get("user_data", {})
        account.telegram_user_id = str(user_data.get("id")) if user_data.get("id") else None
        account.telegram_username = user_data.get("username")
        account.first_name = user_data.get("first_name")
        account.authorized_at = datetime.now(timezone.utc)
        account.last_error = None
        await self.db.commit()
        return payload

    async def stop(self, session_name: str, _remove_container: bool) -> dict:
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if not account:
            raise BusinessError("Session not found", status_code=500)
        payload = await session_manager.stop(session_name)
        account.status = "stopped"
        await self.db.commit()
        return payload

    async def restart(self, session_name: str) -> dict:
        result = await self.db.execute(
            select(TelegramAccount, TelegramApp)
            .join(TelegramApp, TelegramApp.id == TelegramAccount.telegram_app_id)
            .where(TelegramAccount.session_name == session_name)
        )
        row = result.first()
        if not row:
            raise BusinessError("Session not found", status_code=500)
        account, app = row

        payload = await session_manager.restart(
            session_name=account.session_name,
            api_id=int(app.api_id),
            api_hash=decrypt_text(app.api_hash_encrypted) or "",
            account_type=account.type,
            phone=account.phone,
            bot_token=decrypt_text(account.bot_token_encrypted),
        )
        account.status = payload.get("status", account.status)
        await self.db.commit()
        return payload

    async def status(self, session_name: str) -> dict:
        result = await self.db.execute(select(TelegramAccount).where(TelegramAccount.session_name == session_name))
        account = result.scalar_one_or_none()
        if not account:
            raise BusinessError("Session not found", status_code=404)

        runtime = session_manager.compatibility_runtime(session_name)
        return {
            "session_name": account.session_name,
            "status": account.status,
            "type": account.type,
            "has_container": runtime["has_container"],
            "container_name": runtime["container_name"],
            "container_port": runtime["container_port"],
            "phone": account.phone,
            "telegram_username": account.telegram_username,
            "first_name": account.first_name,
            "last_error": account.last_error,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }
