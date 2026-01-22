from typing import Annotated, Any, Literal, Optional, Union
from uuid import UUID

from pydantic import ConfigDict, Field, SecretStr
from pydantic import field_validator
import orjson

from src.core.enums import Currency, PaymentGatewayType, YookassaVatCode

from .base import TrackableDto


class PaymentResult(TrackableDto):
    id: UUID
    url: Optional[str] = None


class PaymentGatewayDto(TrackableDto):
    id: Optional[int] = Field(default=None, frozen=True)

    order_index: int
    type: PaymentGatewayType
    currency: Currency

    is_active: bool
    settings: Optional["AnyGatewaySettingsDto"] = None

    @property
    def requires_webhook(self) -> bool:
        return self.type not in {
            PaymentGatewayType.CRYPTOMUS,
            PaymentGatewayType.HELEKET,
        }


class GatewaySettingsDto(TrackableDto):
    model_config = ConfigDict(validate_assignment=True)

    @property
    def is_configure(self) -> bool:
        for name, value in self.__dict__.items():
            if value is None:
                return False
        return True

    @property
    def get_settings_as_list_data(self) -> list[dict[str, Any]]:
        return [
            {"field": field_name, "value": value}
            for field_name, value in self.__dict__.items()
            if field_name != "type"
        ]


class YookassaGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.YOOKASSA] = PaymentGatewayType.YOOKASSA
    shop_id: Optional[str] = None
    api_key: Optional[SecretStr] = None
    customer: Optional[str] = None
    vat_code: Optional[YookassaVatCode] = None


class YoomoneyGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.YOOMONEY] = PaymentGatewayType.YOOMONEY
    wallet_id: Optional[str] = None
    secret_key: Optional[SecretStr] = None


class CryptomusGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.CRYPTOMUS] = PaymentGatewayType.CRYPTOMUS
    merchant_id: Optional[str] = None
    api_key: Optional[SecretStr] = None


class HeleketGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.HELEKET] = PaymentGatewayType.HELEKET
    merchant_id: Optional[str] = None
    api_key: Optional[SecretStr] = None


class CryptopayGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.CRYPTOPAY] = PaymentGatewayType.CRYPTOPAY
    shop_id: Optional[str] = None
    api_key: Optional[SecretStr] = None
    secret_key: Optional[SecretStr] = None


class RobokassaGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.ROBOKASSA] = PaymentGatewayType.ROBOKASSA
    shop_id: Optional[str] = None
    api_key: Optional[SecretStr] = None
    secret_key: Optional[SecretStr] = None


class TributeGatewaySettingsDto(GatewaySettingsDto):
    type: Literal[PaymentGatewayType.TRIBUTE] = PaymentGatewayType.TRIBUTE
    api_key: Optional[SecretStr] = None
    donate_link: Optional[SecretStr] = None
    subscription_link: Optional[SecretStr] = None
    plan_id: Optional[int] = None
    period_map_json: Optional[str] = None

    @property
    def is_configure(self) -> bool:
        if not self.api_key:
            return False
        if self.plan_id is None:
            return False
        if not (self.subscription_link or self.donate_link):
            return False
        # For subscriptions we must know how to map Tribute periods -> bot durations.
        if self.subscription_link and not self.period_map_json:
            return False
        return True

    @field_validator("period_map_json")
    @classmethod
    def validate_period_map_json(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            loaded = orjson.loads(v.encode("utf-8"))
        except Exception as exc:
            raise ValueError("period_map_json must be a valid JSON object") from exc
        if not isinstance(loaded, dict):
            raise ValueError("period_map_json must be a JSON object")
        # values should be ints (days)
        for key, value in loaded.items():
            try:
                int(value)
            except Exception as exc:
                raise ValueError(
                    f"period_map_json['{key}'] must be an integer number of days"
                ) from exc
        return v


AnyGatewaySettingsDto = Annotated[
    Union[
        YookassaGatewaySettingsDto,
        YoomoneyGatewaySettingsDto,
        CryptomusGatewaySettingsDto,
        HeleketGatewaySettingsDto,
        CryptopayGatewaySettingsDto,
        RobokassaGatewaySettingsDto,
        TributeGatewaySettingsDto,
    ],
    Field(discriminator="type"),
]
