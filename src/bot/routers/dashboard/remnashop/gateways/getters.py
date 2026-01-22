from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.core.config import AppConfig
from src.core.enums import Currency
from src.infrastructure.database.models.dto import PaymentGatewayDto
from src.services.payment_gateway import PaymentGatewayService
from src.services.settings import SettingsService


@inject
async def gateways_getter(
    dialog_manager: DialogManager,
    payment_gateway_service: FromDishka[PaymentGatewayService],
    **kwargs: Any,
) -> dict[str, Any]:
    gateways: list[PaymentGatewayDto] = await payment_gateway_service.get_all()

    formatted_gateways = [
        {
            "id": gateway.id,
            "gateway_type": gateway.type,
            "is_active": gateway.is_active,
        }
        for gateway in gateways
    ]

    return {
        "gateways": formatted_gateways,
    }


@inject
async def gateway_getter(
    dialog_manager: DialogManager,
    config: AppConfig,
    payment_gateway_service: FromDishka[PaymentGatewayService],
    **kwargs: Any,
) -> dict[str, Any]:
    gateway_id = dialog_manager.dialog_data["gateway_id"]
    gateway = await payment_gateway_service.get(gateway_id=gateway_id)

    if not gateway:
        raise ValueError(f"Gateway '{gateway_id}' not found")

    if not gateway.settings:
        raise ValueError(f"Gateway '{gateway_id}' has not settings")

    return {
        "id": gateway.id,
        "gateway_type": gateway.type,
        "is_active": gateway.is_active,
        "settings": gateway.settings.get_settings_as_list_data,
        "webhook": config.get_webhook(gateway.type),
        "requires_webhook": gateway.requires_webhook,
    }


@inject
async def field_getter(
    dialog_manager: DialogManager,
    payment_gateway_service: FromDishka[PaymentGatewayService],
    **kwargs: Any,
) -> dict[str, Any]:
    gateway_id = dialog_manager.dialog_data["gateway_id"]
    selected_field = dialog_manager.dialog_data["selected_field"]

    gateway = await payment_gateway_service.get(gateway_id=gateway_id)

    if not gateway:
        raise ValueError(f"Gateway '{gateway_id}' not found")

    if not gateway.settings:
        raise ValueError(f"Gateway '{gateway_id}' has not settings")

    hint: Any = False
    if gateway.type.value == "TRIBUTE":
        if selected_field == "api_key":
            hint = "API-ключ Tribute из панели автора (используется для проверки подписи webhook)."
        elif selected_field == "subscription_link":
            hint = (
                "Ссылка на подписку Tribute (её даём пользователю). "
                "Для подписки сумма в URL не передаётся."
            )
        elif selected_field == "donate_link":
            hint = (
                "Ссылка на донат Tribute. Используй только если принимаешь донаты "
                "(тогда бот добавляет amount в URL)."
            )
        elif selected_field == "plan_id":
            hint = (
                "ID тарифа Remnashop, который выдавать/продлевать после оплаты. "
                "ID теперь видно в «Конфигураторе плана»."
            )
        elif selected_field == "period_map_json":
            hint = (
                "JSON-объект маппинга «период/сумма → дни». Рекомендуется строгий режим.\n"
                "Пример для 1 месяца за 100₽:\n"
                "{\"amount:10000\": 30}\n"
                "Сумма указывается в копейках."
            )

    return {
        "gateway_type": gateway.type,
        "field": selected_field,
        "hint": hint,
    }


@inject
async def currency_getter(
    dialog_manager: DialogManager,
    settings_service: FromDishka[SettingsService],
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "currency_list": [
            {
                "symbol": currency.symbol,
                "currency": currency.value,
                "enabled": currency == await settings_service.get_default_currency(),
            }
            for currency in Currency
        ]
    }


@inject
async def placement_getter(
    dialog_manager: DialogManager,
    payment_gateway_service: FromDishka[PaymentGatewayService],
    **kwargs: Any,
) -> dict[str, Any]:
    gateways: list[PaymentGatewayDto] = await payment_gateway_service.get_all(sorted=True)

    formatted_gateways = [
        {
            "id": gateway.id,
            "gateway_type": gateway.type,
            "is_active": gateway.is_active,
        }
        for gateway in gateways
    ]

    return {
        "gateways": formatted_gateways,
    }
