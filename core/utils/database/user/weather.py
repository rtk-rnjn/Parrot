from __future__ import annotations

from typing import Any

from ..mixin import DatabaseMixin


class _UserWeatherMixin(DatabaseMixin):
    """Default location, units and language for the weather commands, stored as ``weather`` on the user document."""

    async def get_weather_settings(self, user_id: int, /):
        document = await self.users_collection.find_one({"_id": user_id}, {"weather": 1})
        return (document or {}).get("weather") or {}

    async def update_weather_settings(self, user_id: int, /, **fields: Any) -> None:
        if not fields:
            return
        updates = {f"weather.{key}": value for key, value in fields.items()}
        await self.users_collection.update_one({"_id": user_id}, {"$set": updates}, upsert=True)

    async def remove_weather_location(self, user_id: int, /) -> bool:
        result = await self.users_collection.update_one({"_id": user_id}, {"$unset": {"weather.location": ""}})
        return result.modified_count > 0
