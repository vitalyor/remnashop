import hashlib
import hmac
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID, uuid5, NAMESPACE_URL

import orjson
from fastapi import Request
from loguru import logger

from src.core.enums import Currency, PaymentGatewayType, PurchaseType, TransactionStatus
from src.infrastructure.database.models.dto import (
    PaymentGatewayDto,
    PaymentResult,
    PlanSnapshotDto,
    PriceDetailsDto,
    TransactionDto,
    TributeGatewaySettingsDto,
)

from .base import BasePaymentGateway


class TributeGateway(BasePaymentGateway):
    def __init__(
        self,
        gateway: PaymentGatewayDto,
        bot,
        config,
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

        if not isinstance(self.data.settings, TributeGatewaySettingsDto):
            raise TypeError(
                f"Invalid settings type: expected {TributeGatewaySettingsDto.__name__}, "
                f"got {type(self.data.settings).__name__}"
            )

        if self.data.type != PaymentGatewayType.TRIBUTE:
            raise ValueError(f"TributeGateway initialized with wrong type '{self.data.type}'")

    async def handle_create_payment(self, user, amount: Decimal, details: str) -> PaymentResult:
        payment_id = uuid.uuid4()

        if not self.data.settings:
            raise ValueError("TRIBUTE settings are not configured")

        amount_kopeks = int((amount * 100).to_integral_value())

        is_subscription_link = bool(self.data.settings.subscription_link)
        raw_link = ""
        if self.data.settings.subscription_link:
            raw_link = self.data.settings.subscription_link.get_secret_value().strip()
        elif self.data.settings.donate_link:
            raw_link = self.data.settings.donate_link.get_secret_value().strip()

        if not raw_link:
            raise ValueError("TRIBUTE subscription_link/donate_link is not configured")

        url = urlparse(raw_link)
        query = dict(parse_qsl(url.query, keep_blank_values=True))
        query.update(
            {
                "telegram_user_id": str(user.telegram_id),
                "order_id": str(payment_id),
            }
        )
        # Donation link expects "amount". Subscription links usually have fixed periods/prices,
        # so we don't force amount into the URL (it may be ignored or rejected by Tribute).
        if not is_subscription_link:
            query["amount"] = str(amount_kopeks)

        final_url = urlunparse(url._replace(query=urlencode(query)))

        logger.info(
            f"Created Tribute payment link for user '{user.telegram_id}', "
            f"amount={amount_kopeks} kopeks, payment_id={payment_id}"
        )
        return PaymentResult(id=payment_id, url=final_url)

    async def handle_webhook(self, request: Request) -> tuple[UUID, TransactionStatus]:
        raw_body = await request.body()
        if not raw_body:
            raise ValueError("Empty webhook body")

        signature = request.headers.get("trbt-signature")
        if not signature:
            raise PermissionError("Missing 'trbt-signature' header")

        if not self.data.settings or not self.data.settings.api_key:
            raise PermissionError("TRIBUTE api_key is not configured")

        payload = raw_body.decode("utf-8")
        expected_signature = hmac.new(
            self.data.settings.api_key.get_secret_value().encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise PermissionError("Invalid Tribute webhook signature")

        try:
            webhook_data = orjson.loads(raw_body)
        except orjson.JSONDecodeError as exc:
            raise ValueError("Invalid JSON") from exc

        if not isinstance(webhook_data, dict):
            raise ValueError("Webhook payload is not an object")

        payment_status = _extract_status(webhook_data)

        # Not a payment event (e.g. auto-renew canceled) -> no-op.
        if payment_status is None:
            logger.info("Tribute webhook ignored (non-payment event)")
            return uuid.uuid4(), TransactionStatus.CANCELED

        telegram_user_id = _extract_user_id(webhook_data)
        amount_kopeks = _extract_amount(webhook_data)
        external_id = _extract_external_id(webhook_data)

        if not self.transaction_service or not self.user_service or not self.plan_service or not self.subscription_service:
            raise RuntimeError("Required services are not available in TributeGateway")

        settings = self.data.settings
        if settings.plan_id is None:
            raise ValueError("TRIBUTE plan_id is not configured")

        plan = await self.plan_service.get(settings.plan_id)
        if not plan:
            raise ValueError(f"TRIBUTE plan_id '{settings.plan_id}' not found")

        payment_id = _make_payment_uuid(external_id)
        existing = await self.transaction_service.get(payment_id)
        if existing and existing.is_completed:
            return payment_id, TransactionStatus.COMPLETED

        if payment_status == TransactionStatus.CANCELED:
            if existing:
                existing.status = TransactionStatus.CANCELED
                await self.transaction_service.update(existing)
            return payment_id, TransactionStatus.CANCELED

        if telegram_user_id is None:
            raise ValueError("Missing user id in Tribute webhook")

        user = await self.user_service.get_or_create_stub(telegram_user_id)

        if existing and existing.user and existing.user.telegram_id != user.telegram_id:
            raise ValueError(
                "Tribute webhook user mismatch for existing transaction: "
                f"tx_user={existing.user.telegram_id}, webhook_user={user.telegram_id}"
            )

        duration_days = _extract_duration_days(webhook_data, settings.period_map_json)
        duration = plan.get_duration(duration_days)
        if not duration:
            raise ValueError(
                f"Plan '{plan.id}' has no duration '{duration_days}' days for TRIBUTE"
            )

        plan_snapshot = PlanSnapshotDto.from_plan(plan, duration_days)

        subscription = await self.subscription_service.get_current(user.telegram_id)
        purchase_type = PurchaseType.RENEW if subscription else PurchaseType.NEW

        pricing_rub = (
            Decimal(amount_kopeks) / Decimal(100) if amount_kopeks is not None else Decimal(0)
        )
        pricing = PriceDetailsDto(original_amount=pricing_rub, final_amount=pricing_rub)

        if existing:
            # Webhook is the source of truth: update pending/canceled/failed tx to match
            # what Tribute actually charged and which period was purchased.
            existing.status = TransactionStatus.PENDING
            existing.purchase_type = purchase_type
            existing.gateway_type = PaymentGatewayType.TRIBUTE
            existing.pricing = pricing
            existing.currency = Currency.RUB
            existing.plan = plan_snapshot
            await self.transaction_service.update(existing)
        else:
            tx = TransactionDto(
                payment_id=payment_id,
                status=TransactionStatus.PENDING,
                purchase_type=purchase_type,
                gateway_type=PaymentGatewayType.TRIBUTE,
                pricing=pricing,
                currency=Currency.RUB,
                plan=plan_snapshot,
            )
            await self.transaction_service.create(user, tx)

        return payment_id, TransactionStatus.COMPLETED


def _extract_status(data: dict[str, Any]) -> TransactionStatus | None:
    event_name = data.get("name")
    if isinstance(event_name, str) and event_name.strip().lower() in {
        "cancelled_subscription",
        "canceled_subscription",
        "subscription_canceled",
        "subscription_cancelled",
    }:
        # Subscription cancellation is not a payment event (we don't revoke access immediately).
        return None

    status = data.get("status")
    payload = data.get("payload")

    if not status and isinstance(payload, dict):
        status = payload.get("status")

    if not status and "name" in data and isinstance(payload, dict):
        if event_name == "new_donation":
            status = "paid"

    if isinstance(status, str):
        normalized = status.strip().lower()
        if normalized in {"paid", "success", "succeeded", "completed"}:
            return TransactionStatus.COMPLETED
        if normalized in {"cancel", "canceled", "cancelled", "failed", "error"}:
            return TransactionStatus.CANCELED

    raise ValueError(f"Unsupported Tribute status: {status}")


def _extract_user_id(data: dict[str, Any]) -> int | None:
    payload = data.get("payload")
    value = data.get("telegram_user_id") or data.get("user_id")
    if value is None and isinstance(payload, dict):
        value = payload.get("telegram_user_id") or payload.get("user_id")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_amount(data: dict[str, Any]) -> int | None:
    payload = data.get("payload")
    value = data.get("amount")
    if value is None and isinstance(payload, dict):
        value = payload.get("amount")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _extract_external_id(data: dict[str, Any]) -> str:
    payload = data.get("payload")
    candidates = [
        data.get("order_id"),
        data.get("payment_id"),
        data.get("id"),
        data.get("donation_request_id"),
    ]
    if isinstance(payload, dict):
        candidates.extend(
            [
                payload.get("order_id"),
                payload.get("payment_id"),
                payload.get("id"),
                payload.get("donation_request_id"),
            ]
        )

    for c in candidates:
        if c is None:
            continue
        s = str(c).strip()
        if s:
            return s

    # Fallback: stable-ish id from whole payload
    return orjson.dumps(data).decode("utf-8")


def _make_payment_uuid(external_id: str) -> UUID:
    try:
        return UUID(str(external_id))
    except Exception:
        return uuid5(NAMESPACE_URL, f"tribute:{external_id}")


def _extract_duration_days(data: dict[str, Any], period_map_json: str | None) -> int:
    payload = data.get("payload")

    raw_days = data.get("duration_days")
    if raw_days is None and isinstance(payload, dict):
        raw_days = payload.get("duration_days") or payload.get("days")
    try:
        if raw_days is not None:
            return int(raw_days)
    except (TypeError, ValueError):
        pass

    mapping: dict[str, int] = {}
    if period_map_json:
        try:
            loaded = orjson.loads(period_map_json.encode("utf-8"))
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    try:
                        mapping[str(k)] = int(v)
                    except Exception:
                        continue
        except Exception:
            raise ValueError("TRIBUTE period_map_json is not a valid JSON object")

    strict_mode = any(":" in k for k in mapping.keys())

    # Try map by tribute period/product identifiers
    keys_to_try: list[str] = []
    id_fields = [
        "period_id",
        "subscription_period_id",
        "period",
        "subscription_period",
        "period_name",
        "product_id",
        "subscription_id",
        "tier_id",
    ]
    for field in id_fields:
        v = data.get(field)
        if v is None and isinstance(payload, dict):
            v = payload.get(field)
        if v is None:
            continue
        if strict_mode:
            keys_to_try.append(f"{field}:{v}")
        else:
            keys_to_try.append(str(v))

    amount = _extract_amount(data)
    if amount is not None:
        if strict_mode:
            keys_to_try.append(f"amount:{amount}")
        else:
            keys_to_try.append(str(amount))

    for k in keys_to_try:
        if k in mapping:
            return mapping[k]

    raise ValueError(
        "Unable to determine duration for Tribute payment; "
        "set TRIBUTE period_map_json or provide duration_days in webhook. "
        "Tip: for strict mapping use keys like 'period_id:123' or 'amount:25000'"
    )
