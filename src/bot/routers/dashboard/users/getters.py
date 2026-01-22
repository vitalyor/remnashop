from math import ceil
from typing import Any, cast

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.core.utils.formatters import format_percent
from src.infrastructure.database.models.dto import UserDto
from src.services.user import UserService


PAGE_SIZE = 10


def _user_label(user: UserDto) -> str:
    username = user.username or "no_username"
    return f"@{username} ({user.telegram_id})"


def _get_page(dialog_manager: DialogManager, key: str) -> int:
    page = dialog_manager.dialog_data.get(key, 1)
    try:
        page_int = int(page)
    except (TypeError, ValueError):
        page_int = 1
    return max(1, page_int)


def _paginate(
    items: list[UserDto],
    page: int,
) -> tuple[list[UserDto], int]:
    total_pages = max(1, ceil(len(items) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    return items[start:end], page


async def search_results_getter(dialog_manager: DialogManager, **kwargs: Any) -> dict[str, Any]:
    start_data = cast(dict[str, Any], dialog_manager.start_data)
    found_users_data: list[str] = start_data["found_users"]
    found_users: list[UserDto] = [
        UserDto.model_validate_json(json_string) for json_string in found_users_data
    ]

    page = _get_page(dialog_manager, "page_search_results")
    page_users, page = _paginate(found_users, page)
    pages = max(1, ceil(len(found_users) / PAGE_SIZE))

    return {
        "found_users": [
            {"telegram_id": u.telegram_id, "label": _user_label(u)} for u in page_users
        ],
        "count": len(found_users),
        "page": page,
        "pages": pages,
        "show_pager": len(found_users) > PAGE_SIZE,
    }


@inject
async def all_users_getter(
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    **kwargs: Any,
) -> dict[str, Any]:
    users = await user_service.get_all()
    page = _get_page(dialog_manager, "page_all_users")
    page_users, page = _paginate(users, page)
    pages = max(1, ceil(len(users) / PAGE_SIZE))
    return {
        "all_users": [{"telegram_id": u.telegram_id, "label": _user_label(u)} for u in page_users],
        "count_users": len(users),
        "page": page,
        "pages": pages,
        "show_pager": len(users) > PAGE_SIZE,
    }


@inject
async def recent_registered_getter(
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    **kwargs: Any,
) -> dict[str, Any]:
    users = await user_service.get_recent_registered_users()
    page = _get_page(dialog_manager, "page_recent_registered")
    page_users, page = _paginate(users, page)
    pages = max(1, ceil(len(users) / PAGE_SIZE))
    return {
        "recent_registered_users": [
            {"telegram_id": u.telegram_id, "label": _user_label(u)} for u in page_users
        ],
        "page": page,
        "pages": pages,
        "show_pager": len(users) > PAGE_SIZE,
    }


@inject
async def recent_activity_getter(
    dialog_manager: DialogManager,
    user: UserDto,
    user_service: FromDishka[UserService],
    **kwargs: Any,
) -> dict[str, Any]:
    users = await user_service.get_recent_activity_users(excluded_ids=[user.telegram_id])
    page = _get_page(dialog_manager, "page_recent_activity")
    page_users, page = _paginate(users, page)
    pages = max(1, ceil(len(users) / PAGE_SIZE))
    return {
        "recent_activity_users": [
            {"telegram_id": u.telegram_id, "label": _user_label(u)} for u in page_users
        ],
        "page": page,
        "pages": pages,
        "show_pager": len(users) > PAGE_SIZE,
    }


@inject
async def blacklist_getter(
    dialog_manager: DialogManager,
    user_service: FromDishka[UserService],
    **kwargs: Any,
) -> dict[str, Any]:
    blocked_users = await user_service.get_blocked_users()
    count_users = await user_service.count()
    page = _get_page(dialog_manager, "page_blacklist")
    page_users, page = _paginate(blocked_users, page)
    pages = max(1, ceil(len(blocked_users) / PAGE_SIZE))

    return {
        "blocked_users_exists": bool(blocked_users),
        "blocked_users": [
            {"telegram_id": u.telegram_id, "label": _user_label(u)} for u in page_users
        ],
        "count_blocked": len(blocked_users),
        "count_users": count_users,
        "percent": format_percent(part=len(blocked_users), whole=count_users),
        "page": page,
        "pages": pages,
        "show_pager": len(blocked_users) > PAGE_SIZE,
    }
