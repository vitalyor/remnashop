# Remnashop — заметки по доработкам (админка + Tribute)

Этот документ описывает, **что было изменено** в проекте и **где это искать** в коде:

- админка: списки пользователей + удаление из БД + пагинация
- админка: Remnawave (Hosts/Nodes/Inbounds) с нормальными списками и пагинацией
- платежи: новый шлюз **Tribute** (ориентация на подписки) и обработка webhook

## 1) Админка → Пользователи

### 1.1. “Все пользователи”

Добавлен пункт меню “Все пользователи”, который показывает **список всех пользователей** из БД.

Код:
- `src/bot/routers/dashboard/users/dialog.py`
- `src/bot/routers/dashboard/users/getters.py` (getter `all_users_getter`)
- `src/bot/routers/dashboard/users/handlers.py` (обработчики пагинации)

### 1.2. Формат текста на кнопках пользователей

Кнопки пользователей в списках отображаются так:

`@username (telegram_id)`

Если `username` отсутствует, используется `@no_username`.

Код:
- `src/bot/routers/dashboard/users/getters.py` → `_user_label()`

### 1.3. Пагинация в списках пользователей

Пагинация сделана единым стилем:

- размер страницы: `10` (`PAGE_SIZE = 10`)
- кнопки: `< 1/12 >` (без “первой/последней” страницы)
- показывается **только если элементов больше 10**

Код:
- `src/bot/routers/dashboard/users/getters.py` → `_paginate()` и `show_pager`
- `src/bot/routers/dashboard/users/dialog.py` → `Row(<, page/pages, >, when=show_pager)`
- `src/bot/routers/dashboard/users/handlers.py` → `on_*_prev/on_*_next`

### 1.4. Удаление пользователя из БД (в карточке пользователя)

В карточке пользователя добавлена кнопка “удалить из базы данных”.
Удаление защищено **подтверждением двойным нажатием** (double click confirm).

Код UI:
- `src/bot/routers/dashboard/users/user/dialog.py`
- `src/bot/routers/dashboard/users/user/handlers.py` → `on_user_delete_db()`

Код удаления (серверная логика):
- `src/services/user.py` → `UserService.delete()`

Что удаляется, чтобы не ловить FK-ошибки:
- активации промокодов пользователя
- транзакции пользователя
- реферальные связи пользователя
- сам пользователь

Связанные репозитории:
- `src/infrastructure/database/repositories/promocode_activation.py` (новый репозиторий)
- `src/infrastructure/database/repositories/facade.py` (подключение `promocode_activations`)

## 2) Админка → Remnawave (Hosts/Nodes/Inbounds)

Раньше поведение выглядело как “одна сущность = одна страница” и при большом количестве
визуально воспринималось как “пагинация есть”, но фактически это был не список/выбор.

Сейчас сделано так:

- отдельный **список** (Hosts/Nodes/Inbounds)
- клик по элементу открывает отдельный **детальный экран**
- пагинация `< 1/12 >`, размер страницы 10, отображается только когда элементов > 10

Код:
- `src/bot/states.py` → добавлены состояния `DashboardRemnawave.HOST/NODE/INBOUND`
- `src/bot/routers/dashboard/remnawave/dialog.py` (list + detail окна + pager)
- `src/bot/routers/dashboard/remnawave/getters.py` (формирование списка + деталей + page slicing)
- `src/bot/routers/dashboard/remnawave/handlers.py` (select + next/prev)

Техническая деталь:
- в `dialog_manager.dialog_data` сохраняются заранее подготовленные строки деталей
  (`hosts_details`, `nodes_details`, `inbounds_details`), а выбор идёт по индексу `idx`.

## 3) Платёжный шлюз TRIBUTE (под подписки)

### 3.1. Где включается тип шлюза

Тип добавлен как `PaymentGatewayType.TRIBUTE`.

Код:
- `src/core/enums.py` → `PaymentGatewayType.TRIBUTE` + `Currency.from_gateway_type()`
- `assets/translations/ru/utils.ftl` → отображаемое имя “Tribute”

Для PostgreSQL enum добавлена миграция:
- `src/infrastructure/database/migrations/versions/0018_add_tribute_gateway_type.py`

### 3.2. Настройки шлюза (в админке Remnashop → Gateways)

DTO настроек:
- `src/infrastructure/database/models/dto/payment_gateway.py` → `TributeGatewaySettingsDto`

Поля:
- `api_key` — ключ Tribute (используется для проверки подписи webhook)
- `plan_id` — ID тарифа Remnashop, который будет выдаваться/продлеваться после оплаты
- `subscription_link` **или** `donate_link` — ссылка Tribute
- `period_map_json` — JSON-маппинг “период Tribute → дни в Remnashop”

Правила “configured” (защита от дурака):
- обязательно: `api_key`, `plan_id`, и хотя бы одна ссылка (`subscription_link` или `donate_link`)
- если указан `subscription_link`, то `period_map_json` обязателен

Код:
- `src/infrastructure/database/models/dto/payment_gateway.py` → `TributeGatewaySettingsDto.is_configure`
- там же валидируется `period_map_json` (должен быть JSON-объект, значения приводимы к `int`)

### 3.3. Ограничение TRIBUTE только на “свой” тариф/периоды (защита от неверного выбора)

В меню выбора способа оплаты для пользователя TRIBUTE показывается только если:

- выбран тариф, который совпадает с `TRIBUTE.plan_id`
- (опционально) выбранная длительность есть в `period_map_json`, если он задан

Код:
- `src/bot/routers/subscription/getters.py` → `payment_method_getter()`

### 3.4. Создание ссылки на оплату

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `TributeGateway.handle_create_payment()`

Поведение:
- генерируется `order_id` (UUID), он же станет `payment_id` в нашей системе
- в URL добавляются параметры:
  - `telegram_user_id`
  - `order_id`
- параметр `amount` добавляется **только для donate_link**
  - для `subscription_link` сумма не форсится (обычно у подписки фиксированные периоды/цены на стороне Tribute)

### 3.5. Webhook: подпись, идемпотентность, выдача подписки

#### Точка входа

Webhook принимается в FastAPI:
- `src/api/endpoints/payments.py` → `POST /api/v1/payments/{gateway_type}`

Дальше запускается стандартный пайплайн:
- `src/infrastructure/taskiq/tasks/payments.py` → `handle_payment_transaction_task()`
- `src/services/payment_gateway.py` → `handle_payment_succeeded()/handle_payment_canceled()`
- `src/infrastructure/taskiq/tasks/subscriptions.py` → `purchase_subscription_task()`

#### Проверка подписи (TRIBUTE)

Сейчас ожидается заголовок:
- `trbt-signature`

Алгоритм:
- `expected = HMAC_SHA256(api_key, raw_body).hexdigest()`
- сравнение через `hmac.compare_digest`

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `TributeGateway.handle_webhook()`

#### Идемпотентность / защита от дублей

Мы стараемся извлечь внешний идентификатор (`external_id`) из webhook:
- `order_id`, `payment_id`, `id`, `donation_request_id` (и то же внутри `payload`)

Дальше делаем `payment_id`:
- если `external_id` уже UUID → используем как есть
- иначе → `uuid5(NAMESPACE_URL, f"tribute:{external_id}")`

Это позволяет **безопасно** переживать повторные webhook’и:
- если транзакция уже `COMPLETED`, повторный webhook ничего не выдаёт повторно

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `_extract_external_id()`, `_make_payment_uuid()`

#### Определение статуса события

- если это “не платёжное событие” (например, `cancelled_subscription`) → это **no-op**
  (мы не отзываем доступ мгновенно)
- если статус платёжный:
  - `COMPLETED` → продолжим пайплайн выдачи подписки
  - `CANCELED` → отметим транзакцию отменённой (если она уже была)

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `_extract_status()`

#### Маппинг периода Tribute → длительность подписки в днях

Бот должен понять, **на сколько дней** продлевать/выдавать подписку.
Есть 2 способа:

1) Tribute прислал явные `duration_days/days` в webhook → используем их.
2) Иначе используем `period_map_json`.

`period_map_json` — это JSON-объект `"ключ": дни`.

Есть два режима:

1) Обычный (legacy): ключи без двоеточия (можно маппить напрямую по `period_id` или даже по сумме)
```json
{
  "1": 30,
  "3": 90,
  "25000": 30
}
```

2) Строгий (рекомендуемый): ключи с префиксом `field:value`
```json
{
  "period_id:1": 30,
  "period_id:3": 90,
  "amount:25000": 30
}
```

В строгом режиме мы **не будем** использовать “голые” значения, только `field:value`.

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `_extract_duration_days()`

#### Привязка к тарифу Remnashop

TRIBUTE привязан к одному тарифу через `plan_id` (настройка шлюза).
На webhook мы:

- грузим тариф `plan_id`
- определяем `duration_days`
- проверяем, что у тарифа есть такая длительность
- создаём/обновляем транзакцию с `plan_snapshot = PlanSnapshotDto.from_plan(plan, duration_days)`

Дальше уже стандартная логика:
- если у пользователя уже есть активная подписка → `PurchaseType.RENEW`
- иначе → `PurchaseType.NEW`

Код:
- `src/infrastructure/payment_gateways/tribute.py` → `handle_webhook()`
- `src/infrastructure/taskiq/tasks/subscriptions.py` → `purchase_subscription_task()`

#### Важная деталь про пользователя в webhook

Если webhook пришёл на пользователя, которого нет в нашей БД, создаётся “stub user”:
- `src/services/user.py` → `UserService.get_or_create_stub()`

Это нужно, чтобы webhook мог корректно выдать подписку по `telegram_user_id`.

## 4) Ограничения / что может потребовать доработки

Tribute webhook-схема для подписок не подтверждена официальными примерами (в репо `Tribute.MD`
есть только пример `GET /products`). Поэтому:

- поля статуса/периода могут отличаться → тогда надо подстроить `_extract_status()` и `_extract_duration_days()`
- если Tribute умеет “предвыбор периода” через URL, это можно будет добавить в `handle_create_payment()`
  (сейчас ссылка не заставляет период, выбор делается на стороне Tribute)

## 5) Быстрый чек-лист настройки TRIBUTE

1) Применить миграции (важно для enum `payment_gateway_type`).
2) В админке: Remnashop → Gateways → TRIBUTE заполнить:
   - `api_key`
   - `plan_id`
   - `subscription_link`
   - `period_map_json`
3) Включить шлюз (Active).
4) Убедиться, что в меню оплаты у пользователя TRIBUTE появляется только на нужном тарифе/периодах.
5) Снять реальные webhook payload’ы (первый платёж + автопродление) и при необходимости подстроить парсинг.

