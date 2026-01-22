from aiogram import Bot

from src.core.config import AppConfig
from src.infrastructure.database.models.dto import HeleketGatewaySettingsDto, PaymentGatewayDto

from .cryptomus import CryptomusGateway


class HeleketGateway(CryptomusGateway):
    API_BASE: str = "https://api.heleket.com"

    NETWORKS = ["31.133.220.8"]

    def __init__(
        self,
        gateway: PaymentGatewayDto,
        bot: Bot,
        config: AppConfig,
        transaction_service=None,
        user_service=None,
        plan_service=None,
        subscription_service=None,
    ) -> None:
        super().__init__(
            gateway,
            bot,
            config,
            transaction_service=transaction_service,
            user_service=user_service,
            plan_service=plan_service,
            subscription_service=subscription_service,
        )

        if not isinstance(self.data.settings, HeleketGatewaySettingsDto):
            raise TypeError(
                f"Invalid settings type: expected {HeleketGatewaySettingsDto.__name__}, "
                f"got {type(self.data.settings).__name__}"
            )
