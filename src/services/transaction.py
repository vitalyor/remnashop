from decimal import Decimal
from typing import Optional
from uuid import UUID

from aiogram import Bot
from fluentogram import TranslatorHub
from loguru import logger
from redis.asyncio import Redis

from src.core.config import AppConfig
from src.core.enums import PaymentGatewayType, TransactionStatus
from src.infrastructure.database import UnitOfWork
from src.infrastructure.database.models.dto import TransactionDto, UserDto
from src.infrastructure.database.models.sql import Transaction
from src.infrastructure.redis import RedisRepository

from .base import BaseService


class TransactionService(BaseService):
    uow: UnitOfWork

    def __init__(
        self,
        config: AppConfig,
        bot: Bot,
        redis_client: Redis,
        redis_repository: RedisRepository,
        translator_hub: TranslatorHub,
        #
        uow: UnitOfWork,
    ) -> None:
        super().__init__(config, bot, redis_client, redis_repository, translator_hub)
        self.uow = uow

    async def create(self, user: UserDto, transaction: TransactionDto) -> TransactionDto:
        data = transaction.model_dump(exclude={"user"})
        data["plan"] = transaction.plan.model_dump(mode="json")
        data["pricing"] = transaction.pricing.model_dump(mode="json")

        db_transaction = Transaction(**data, user_telegram_id=user.telegram_id)

        async with self.uow:
            db_created_transaction = await self.uow.repository.transactions.create(db_transaction)

        logger.info(f"Created transaction '{transaction.payment_id}' for user '{user.telegram_id}'")
        return TransactionDto.from_model(db_created_transaction)  # type: ignore[return-value]

    async def get(self, payment_id: UUID) -> Optional[TransactionDto]:
        async with self.uow:
            db_transaction = await self.uow.repository.transactions.get(payment_id)

        if db_transaction:
            logger.debug(f"Retrieved transaction '{payment_id}'")
        else:
            logger.warning(f"Transaction '{payment_id}' not found")

        return TransactionDto.from_model(db_transaction)

    async def get_by_user(self, telegram_id: int) -> list[TransactionDto]:
        async with self.uow:
            db_transactions = await self.uow.repository.transactions.get_by_user(telegram_id)

        logger.debug(f"Retrieved '{len(db_transactions)}' transactions for user '{telegram_id}'")
        return TransactionDto.from_model_list(db_transactions)

    async def get_all(self) -> list[TransactionDto]:
        async with self.uow:
            db_transactions = await self.uow.repository.transactions.get_all()

        logger.debug(f"Retrieved '{len(db_transactions)}' total transactions")
        return TransactionDto.from_model_list(db_transactions)

    async def get_by_status(self, status: TransactionStatus) -> list[TransactionDto]:
        async with self.uow:
            db_transactions = await self.uow.repository.transactions.get_by_status(status)

        logger.debug(f"Retrieved '{len(db_transactions)}' transactions with status '{status}'")
        return TransactionDto.from_model_list(db_transactions)

    async def find_recent_pending_by_user_gateway_amount(
        self,
        telegram_user_id: int,
        gateway_type: PaymentGatewayType,
        amount_kopeks: Optional[int],
        limit: int = 10,
    ) -> Optional[TransactionDto]:
        async with self.uow:
            db_transactions = await self.uow.repository.transactions.get_recent_pending_by_user_gateway(
                telegram_id=telegram_user_id,
                gateway_type=gateway_type,
                limit=limit,
            )

        transactions = TransactionDto.from_model_list(db_transactions)

        if amount_kopeks is None:
            return transactions[0] if transactions else None

        for tx in transactions:
            try:
                expected = int((Decimal(tx.pricing.final_amount) * 100).to_integral_value())
            except Exception:
                continue
            if expected == amount_kopeks:
                return tx

        return transactions[0] if transactions else None

    async def update(self, transaction: TransactionDto) -> Optional[TransactionDto]:
        data = transaction.prepare_changed_data()
        data.pop("user", None)

        # JSON columns expect JSON-serializable values (no Decimal / pydantic models).
        if "plan" in data:
            data["plan"] = transaction.plan.model_dump(mode="json")
        if "pricing" in data:
            data["pricing"] = transaction.pricing.model_dump(mode="json")

        async with self.uow:
            db_updated_transaction = await self.uow.repository.transactions.update(
                payment_id=transaction.payment_id,
                **data,
            )

        if db_updated_transaction:
            logger.info(f"Updated transaction '{transaction.payment_id}' successfully")
        else:
            logger.warning(
                f"Attempted to update transaction '{transaction.payment_id}', "
                "but transaction was not found or update failed"
            )

        return TransactionDto.from_model(db_updated_transaction)

    async def count(self) -> int:
        async with self.uow:
            count = await self.uow.repository.transactions.count()

        logger.debug(f"Total transactions count: '{count}'")
        return count

    async def count_by_status(self, status: TransactionStatus) -> int:
        async with self.uow:
            count = await self.uow.repository.transactions.count_by_status(status)

        logger.debug(f"Transactions count with status '{status}': '{count}'")
        return count
