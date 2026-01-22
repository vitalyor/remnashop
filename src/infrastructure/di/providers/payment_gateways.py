from __future__ import annotations

from typing import Type

from aiogram import Bot
from dishka import Provider, Scope, provide
from loguru import logger

from src.core.config import AppConfig
from src.core.enums import PaymentGatewayType
from src.infrastructure.database.models.dto import PaymentGatewayDto
from src.infrastructure.payment_gateways import (
    BasePaymentGateway,
    CryptomusGateway,
    HeleketGateway,
    PaymentGatewayFactory,
    TelegramStarsGateway,
    TributeGateway,
    YookassaGateway,
    YoomoneyGateway,
)
from src.services.plan import PlanService
from src.services.subscription import SubscriptionService
from src.services.transaction import TransactionService
from src.services.user import UserService

GATEWAY_MAP: dict[PaymentGatewayType, Type[BasePaymentGateway]] = {
    PaymentGatewayType.TELEGRAM_STARS: TelegramStarsGateway,
    PaymentGatewayType.YOOKASSA: YookassaGateway,
    PaymentGatewayType.YOOMONEY: YoomoneyGateway,
    PaymentGatewayType.CRYPTOMUS: CryptomusGateway,
    PaymentGatewayType.HELEKET: HeleketGateway,
    PaymentGatewayType.TRIBUTE: TributeGateway,
    # PaymentGatewayType.URLPAY: UrlpayGateway,
}


class PaymentGatewaysProvider(Provider):
    scope = Scope.APP
    _cached_gateways: dict[PaymentGatewayType, BasePaymentGateway] = {}

    @provide()
    def get_gateway_factory(
        self,
        bot: Bot,
        config: AppConfig,
        transaction_service: TransactionService,
        user_service: UserService,
        plan_service: PlanService,
        subscription_service: SubscriptionService,
    ) -> PaymentGatewayFactory:
        def create_gateway(gateway: PaymentGatewayDto) -> BasePaymentGateway:
            gateway_type = gateway.type

            if gateway_type in self._cached_gateways:
                cached_gateway = self._cached_gateways[gateway_type]

                if cached_gateway.data != gateway:
                    logger.warning(
                        f"Gateway '{gateway_type}' data changed. Re-initializing instance"
                    )
                    del self._cached_gateways[gateway_type]

            if gateway_type not in self._cached_gateways:
                gateway_instance = GATEWAY_MAP.get(gateway_type)

                if not gateway_instance:
                    raise ValueError(f"Unknown gateway type '{gateway_type}'")

                self._cached_gateways[gateway_type] = gateway_instance(
                    gateway=gateway,
                    bot=bot,
                    config=config,
                    transaction_service=transaction_service,
                    user_service=user_service,
                    plan_service=plan_service,
                    subscription_service=subscription_service,
                )
                logger.debug(f"Initialized new gateway '{gateway_type}' instance")

            return self._cached_gateways[gateway_type]

        return create_gateway
