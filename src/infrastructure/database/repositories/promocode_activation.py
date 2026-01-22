from src.infrastructure.database.models.sql import PromocodeActivation

from .base import BaseRepository


class PromocodeActivationRepository(BaseRepository):
    async def delete_by_user(self, telegram_id: int) -> int:
        return await self._delete(
            PromocodeActivation,
            PromocodeActivation.user_telegram_id == telegram_id,
        )

