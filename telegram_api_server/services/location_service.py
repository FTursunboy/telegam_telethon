from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from telegram_api_server.models.location_log import LocationLog
from telegram_api_server.schemas.location import CoordinatesItem


class LocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def store_coordinates(self, items: list[CoordinatesItem], is_batch: bool) -> dict[str, Any]:
        created: list[LocationLog] = []
        for item in items:
            row = LocationLog(
                user_id=item.user_id,
                latitude=item.latitude,
                longitude=item.longitude,
                date=item.date,
            )
            self.db.add(row)
            created.append(row)

        await self.db.commit()
        for row in created:
            await self.db.refresh(row)

        data = [
            {
                "id": row.id,
                "user_id": row.user_id,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "date": row.date.isoformat(),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in created
        ]

        return {
            "success": True,
            "saved": len(created),
            "failed": 0,
            "errors": {},
            "data": data if is_batch else (data[0] if data else None),
        }
