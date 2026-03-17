from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api_server.core.auth import ensure_authorized
from telegram_api_server.db.session import get_db
from telegram_api_server.schemas.auth import Complete2FARequest, CompleteCodeRequest, SessionRequest, StartLoginRequest
from telegram_api_server.schemas.location import CoordinatesItem
from telegram_api_server.schemas.messages import EditMessageRequest, SendFileRequest, SendMessageRequest, SendReactionRequest, SendVoiceRequest
from telegram_api_server.services.account_service import AccountService
from telegram_api_server.services.location_service import LocationService
from telegram_api_server.services.message_service import MessageService

router = APIRouter()


async def _authorize(request: Request, fallback: dict[str, Any]) -> None:
    body: Any = fallback
    try:
        body = await request.json()
    except Exception:
        body = fallback
    ensure_authorized(request, body)


@router.post("/api/v1/login/start")
async def login_start(
    payload: StartLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).start_login(payload.model_dump())
    return {"success": True, "data": result}


@router.post("/api/v1/login/complete-code")
async def login_complete_code(
    payload: CompleteCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).complete_code(payload.session_name, payload.code)
    return {"success": True, "data": result}


@router.post("/api/v1/login/complete-2fa")
async def login_complete_2fa(
    payload: Complete2FARequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).complete_2fa(payload.session_name, payload.password)
    return {"success": True, "data": result}


@router.post("/api/v1/session/stop")
async def session_stop(
    payload: SessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).stop(payload.session_name, payload.remove_container if payload.remove_container is not None else True)
    return {"success": True, "data": result}


@router.post("/api/v1/session/restart")
async def session_restart(
    payload: SessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).restart(payload.session_name)
    return {"success": True, "message": "Session restarted", "data": result}


@router.post("/api/v1/session/status")
async def session_status(
    payload: SessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await AccountService(db).status(payload.session_name)
    return {"success": True, "data": result}


@router.post("/api/v1/send-message")
async def send_message(
    payload: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await MessageService(db).send_message(
        payload.session_name,
        payload.peer,
        payload.message,
        payload.parse_mode,
        payload.reply_to_message_id,
    )
    return {"success": True, "data": result}


@router.post("/api/v1/send-voice")
async def send_voice(
    payload: SendVoiceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await MessageService(db).send_voice(
        payload.session_name,
        payload.peer,
        str(payload.voice_url),
        payload.caption,
        payload.reply_to_message_id,
    )
    return {"success": True, "data": result}


@router.post("/api/v1/send-file")
async def send_file(
    payload: SendFileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await MessageService(db).send_file(
        payload.session_name,
        payload.peer,
        str(payload.file_url),
        payload.caption,
        payload.parse_mode,
        payload.reply_to_message_id,
    )
    return {"success": True, "data": result}


@router.post("/api/v1/react-message")
async def react_message(
    payload: SendReactionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await MessageService(db).react_message(
        payload.session_name,
        payload.peer,
        payload.message_id,
        payload.reaction,
        bool(payload.remove),
    )
    return {"success": True, "data": result}


@router.post("/api/v1/edit-message")
async def edit_message(
    payload: EditMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _authorize(request, payload.model_dump())
    result = await MessageService(db).edit_message(
        payload.session_name,
        payload.peer,
        payload.message_id,
        payload.message,
        payload.parse_mode,
    )
    return {"success": True, "data": result}


@router.post("/api/hs/data/coordinates", status_code=201)
async def store_coordinates(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    payload = await request.json()

    is_batch = isinstance(payload, Sequence) and not isinstance(payload, dict)
    items_raw = payload if is_batch else [payload]

    parsed: list[CoordinatesItem] = []
    errors: dict[int, Any] = {}

    for idx, item in enumerate(items_raw):
        try:
            parsed.append(CoordinatesItem.model_validate(item))
        except ValidationError as exc:
            errors[idx] = exc.errors()

    service = LocationService(db)

    if parsed:
        saved = await service.store_coordinates(parsed, is_batch)
    else:
        saved = {
            "success": False,
            "saved": 0,
            "failed": len(errors),
            "errors": errors,
            "data": [] if is_batch else None,
        }

    if errors:
        saved["success"] = False
        saved["failed"] = len(errors)
        saved["errors"] = errors
    return saved
