#!/usr/bin/env python3
"""
Simulate Tribute webhook events for Remnashop.

This is useful because Tribute may not support test payments.

Usage examples:
  python scripts/tribute_mock_webhook.py \
    --base-url http://127.0.0.1:5000 \
    --api-key "YOUR_TRIBUTE_API_KEY" \
    --telegram-user-id 123456789 \
    --duration-days 30 \
    --amount-kopeks 10000

  # Use a specific order_id (e.g. copied from logs/DB)
  python scripts/tribute_mock_webhook.py ... --order-id 550e8400-e29b-41d4-a716-446655440000

  # Simulate cancellation event (non-payment, should be ignored by bot)
  python scripts/tribute_mock_webhook.py ... --event cancelled_subscription
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    # Keep schema aligned with src/infrastructure/payment_gateways/tribute.py extractors:
    # - status can be at root or inside payload
    # - telegram_user_id can be at root or inside payload
    # - order_id/payment_id/id can be at root or inside payload
    # - duration_days can be at root or inside payload (or days)
    data: dict[str, Any] = {
        "name": args.event,
        "order_id": str(args.order_id),
        "telegram_user_id": int(args.telegram_user_id),
        "amount": int(args.amount_kopeks) if args.amount_kopeks is not None else None,
        "duration_days": int(args.duration_days) if args.duration_days is not None else None,
        "status": args.status,
        "payload": {},
    }

    if args.put_fields_in_payload:
        data["payload"] = {
            "order_id": data.pop("order_id"),
            "telegram_user_id": data.pop("telegram_user_id"),
            "amount": data.pop("amount"),
            "duration_days": data.pop("duration_days"),
            "status": data.pop("status"),
        }
        # Root keys expected by some providers
        data["status"] = None

    # Remove nulls to keep payload clean.
    def drop_nulls(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: drop_nulls(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [drop_nulls(v) for v in obj if v is not None]
        return obj

    return drop_nulls(data)


def _sign(api_key: str, body: bytes) -> str:
    return hmac.new(api_key.encode(), body, hashlib.sha256).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Example: http://127.0.0.1:5000")
    parser.add_argument("--api-key", required=True, help="TRIBUTE api_key (used for signature)")
    parser.add_argument(
        "--tribute-url",
        default=None,
        help=(
            "Optional: Tribute payment/subscription URL. "
            "If provided, telegram_user_id and order_id will be parsed from it."
        ),
    )
    parser.add_argument("--telegram-user-id", required=False, type=int)
    parser.add_argument(
        "--amount-kopeks",
        type=int,
        default=None,
        help="Amount in kopeks (100 RUB => 10000). Optional.",
    )
    parser.add_argument(
        "--duration-days",
        type=int,
        default=None,
        help="Duration in days to grant/renew (must exist in selected plan). Optional.",
    )
    parser.add_argument(
        "--order-id",
        type=str,
        default=None,
        help="UUID for order_id/payment_id. If not set, random UUID will be generated.",
    )
    parser.add_argument(
        "--status",
        default="paid",
        help="Payment status. Typical success values: paid/success/succeeded/completed.",
    )
    parser.add_argument(
        "--event",
        default="new_donation",
        help="Event name. For no-op cancellation: cancelled_subscription.",
    )
    parser.add_argument(
        "--put-fields-in-payload",
        action="store_true",
        help="Put order_id/user_id/status/amount/duration_days inside 'payload' object.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout seconds.",
    )

    args = parser.parse_args()

    if args.tribute_url:
        try:
            url = urlparse(args.tribute_url)
            qs = parse_qs(url.query)
            if args.telegram_user_id is None and "telegram_user_id" in qs:
                args.telegram_user_id = int(qs["telegram_user_id"][0])
            if args.order_id is None and "order_id" in qs:
                args.order_id = qs["order_id"][0]
        except Exception as exc:
            print(f"Failed to parse --tribute-url: {exc}", file=sys.stderr)
            return 2

    if args.telegram_user_id is None:
        print("--telegram-user-id is required (or pass --tribute-url with telegram_user_id=...)", file=sys.stderr)
        return 2

    if args.order_id:
        args.order_id = uuid.UUID(str(args.order_id))
    else:
        args.order_id = uuid.uuid4()

    payload = _build_payload(args)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = _sign(args.api_key, body)

    url = args.base_url.rstrip("/") + "/api/v1/payments/tribute"
    headers = {
        "Content-Type": "application/json",
        "trbt-signature": signature,
    }

    print(f"POST {url}")
    print(f"order_id={args.order_id}")
    print(f"event={args.event} status={args.status}")

    if httpx is not None:
        with httpx.Client(timeout=args.timeout) as client:
            resp = client.post(url, content=body, headers=headers)
        status_code = resp.status_code
        text = resp.text
    else:
        req = Request(url=url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req, timeout=args.timeout) as resp:  # nosec - local tooling
                status_code = int(getattr(resp, "status", 200))
                text_bytes = resp.read()
                try:
                    text = text_bytes.decode("utf-8", errors="replace")
                except Exception:
                    text = ""
        except Exception as exc:
            print(f"Request failed: {exc}", file=sys.stderr)
            return 2

    print(f"HTTP {status_code}")
    if text:
        print(text[:2000])

    return 0 if 200 <= status_code < 300 else 2


if __name__ == "__main__":
    raise SystemExit(main())
