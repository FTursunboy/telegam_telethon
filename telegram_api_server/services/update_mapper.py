from __future__ import annotations

from typing import Any

from telethon.tl.types import (
    DocumentAttributeFilename,
    Message,
    MessageMediaContact,
    MessageMediaGeo,
)


class UpdateMapper:
    def map_message(
        self,
        *,
        session_name: str,
        update_type: str,
        message: Message,
        chat: dict[str, Any],
        self_user_id: int | None,
    ) -> dict[str, Any]:
        from_id = self._extract_user_id(message.from_id)
        peer_id = self._extract_user_id(message.peer_id)

        # Compatibility behavior from Laravel service for private/outgoing edge-cases.
        if not bool(message.out) and from_id and peer_id and from_id == peer_id and self_user_id:
            peer_id = self_user_id

        return {
            "session": session_name,
            "update_type": update_type,
            "message_id": message.id,
            "from_id": from_id,
            "peer_id": peer_id,
            "message": message.message,
            "date": int(message.date.timestamp()) if message.date else None,
            "edited": bool(message.edit_date),
            "edit_date": int(message.edit_date.timestamp()) if message.edit_date else None,
            "out": bool(message.out),
            "mentioned": bool(message.mentioned),
            "media": self._map_media(message),
            "reply_to": self._map_reply_to(message),
            "entities": self._map_entities(message.entities),
            "chat": chat,
        }

    @staticmethod
    def _extract_user_id(peer: Any) -> int | None:
        if peer is None:
            return None
        user_id = getattr(peer, "user_id", None)
        if user_id is not None:
            return int(user_id)
        if isinstance(peer, int):
            return peer
        return None

    @staticmethod
    def _map_reply_to(message: Message) -> dict[str, Any] | None:
        if not message.reply_to:
            return None
        reply_to_msg_id = getattr(message.reply_to, "reply_to_msg_id", None)
        if reply_to_msg_id is None:
            return None
        return {"reply_to_msg_id": reply_to_msg_id}

    @staticmethod
    def _map_entities(entities: list[Any] | None) -> list[dict[str, Any]] | None:
        if not entities:
            return None
        result: list[dict[str, Any]] = []
        for entity in entities:
            result.append(
                {
                    "type": entity.__class__.__name__,
                    "offset": getattr(entity, "offset", None),
                    "length": getattr(entity, "length", None),
                    "url": getattr(entity, "url", None),
                    "user_id": getattr(getattr(entity, "user_id", None), "user_id", None),
                    "language": getattr(entity, "language", None),
                }
            )
        return result

    def _map_media(self, message: Message) -> dict[str, Any] | None:
        media = message.media
        if not media:
            return None

        mapped: dict[str, Any] = {
            "type": media.__class__.__name__,
            "has_photo": bool(message.photo),
            "has_document": bool(message.document),
            "has_video": bool(getattr(message, "video", None)),
            "has_audio": bool(getattr(message, "audio", None)),
            "has_voice": bool(getattr(message, "voice", None)),
        }

        if message.photo:
            photo = message.photo
            mapped["photo_id"] = getattr(photo, "id", None)
            mapped["access_hash"] = getattr(photo, "access_hash", None)
            mapped["file_reference"] = self._bytes_to_string(getattr(photo, "file_reference", None))
            mapped["dc_id"] = getattr(photo, "dc_id", None)

        if message.document:
            doc = message.document
            mapped["document_id"] = getattr(doc, "id", None)
            mapped["access_hash"] = getattr(doc, "access_hash", None)
            mapped["file_reference"] = self._bytes_to_string(getattr(doc, "file_reference", None))
            mapped["mime_type"] = getattr(doc, "mime_type", None)
            mapped["size"] = getattr(doc, "size", None)
            mapped["dc_id"] = getattr(doc, "dc_id", None)
            mapped["file_name"] = self._extract_file_name(getattr(doc, "attributes", None))

        if isinstance(media, MessageMediaGeo):
            geo = getattr(media, "geo", None)
            mapped["latitude"] = getattr(geo, "lat", None)
            mapped["longitude"] = getattr(geo, "long", None)

        if isinstance(media, MessageMediaContact):
            mapped["phone_number"] = getattr(media, "phone_number", None)
            mapped["first_name"] = getattr(media, "first_name", None)
            mapped["last_name"] = getattr(media, "last_name", None)
            mapped["user_id"] = getattr(media, "user_id", None)
            mapped["vcard"] = getattr(media, "vcard", None)

        return mapped

    @staticmethod
    def _extract_file_name(attributes: list[Any] | None) -> str | None:
        if not attributes:
            return None
        for attr in attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name
        return None

    @staticmethod
    def _bytes_to_string(value: bytes | None) -> str | None:
        if value is None:
            return None
        try:
            return value.decode("latin-1")
        except Exception:
            return None
