from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Row, Select, Start, SwitchTo
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.bot.keyboards import main_menu_button
from src.bot.states import Dashboard, DashboardUsers
from src.bot.widgets import Banner, I18nFormat, IgnoreUpdate
from src.core.enums import BannerName

from .getters import (
    all_users_getter,
    blacklist_getter,
    recent_activity_getter,
    recent_registered_getter,
    search_results_getter,
)
from .handlers import (
    on_all_users_next,
    on_all_users_prev,
    on_blacklist_next,
    on_blacklist_prev,
    on_page_info,
    on_recent_activity_next,
    on_recent_activity_prev,
    on_recent_registered_next,
    on_recent_registered_prev,
    on_search_results_next,
    on_search_results_prev,
    on_unblock_all,
    on_user_search,
    on_user_select,
)

users = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-main"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-search"),
            id="search",
            state=DashboardUsers.SEARCH,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-recent-registered"),
            id="recent_registered",
            state=DashboardUsers.RECENT_REGISTERED,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-recent-activity"),
            id="recent_activity",
            state=DashboardUsers.RECENT_ACTIVITY,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-blacklist"),
            id="blacklist",
            state=DashboardUsers.BLACKLIST,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-users-all"),
            id="all",
            state=DashboardUsers.ALL,
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-back"),
            id="back",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
        ),
        *main_menu_button,
    ),
    IgnoreUpdate(),
    state=DashboardUsers.MAIN,
)

all_users = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-all", count_users=F["count_users"]),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="user",
            item_id_getter=lambda item: item["telegram_id"],
            items="all_users",
            type_factory=int,
            on_click=on_user_select,
        )
    ),
    Row(
        Button(text=Format("<"), id="prev", on_click=on_all_users_prev, when=F["page"] > 1),
        Button(text=Format("{page}/{pages}"), id="page", on_click=on_page_info),
        Button(
            text=Format(">"),
            id="next",
            on_click=on_all_users_next,
            when=F["page"] < F["pages"],
        ),
        when=F["show_pager"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.ALL,
    getter=all_users_getter,
)

search = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-search"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    MessageInput(func=on_user_search),
    IgnoreUpdate(),
    state=DashboardUsers.SEARCH,
)

recent_registered = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-recent-registered"),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="user",
            item_id_getter=lambda item: item["telegram_id"],
            items="recent_registered_users",
            type_factory=int,
            on_click=on_user_select,
        )
    ),
    Row(
        Button(text=Format("<"), id="prev", on_click=on_recent_registered_prev, when=F["page"] > 1),
        Button(text=Format("{page}/{pages}"), id="page", on_click=on_page_info),
        Button(
            text=Format(">"),
            id="next",
            on_click=on_recent_registered_next,
            when=F["page"] < F["pages"],
        ),
        when=F["show_pager"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.RECENT_REGISTERED,
    getter=recent_registered_getter,
)

recent_activity = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-recent-activity"),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="user",
            item_id_getter=lambda item: item["telegram_id"],
            items="recent_activity_users",
            type_factory=int,
            on_click=on_user_select,
        )
    ),
    Row(
        Button(text=Format("<"), id="prev", on_click=on_recent_activity_prev, when=F["page"] > 1),
        Button(text=Format("{page}/{pages}"), id="page", on_click=on_page_info),
        Button(
            text=Format(">"),
            id="next",
            on_click=on_recent_activity_next,
            when=F["page"] < F["pages"],
        ),
        when=F["show_pager"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.RECENT_ACTIVITY,
    getter=recent_activity_getter,
)

search_results = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-search-results", count=F["count"]),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="user",
            item_id_getter=lambda item: item["telegram_id"],
            items="found_users",
            type_factory=int,
            on_click=on_user_select,
        )
    ),
    Row(
        Button(text=Format("<"), id="prev", on_click=on_search_results_prev, when=F["page"] > 1),
        Button(text=Format("{page}/{pages}"), id="page", on_click=on_page_info),
        Button(
            text=Format(">"),
            id="next",
            on_click=on_search_results_next,
            when=F["page"] < F["pages"],
        ),
        when=F["show_pager"],
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.SEARCH,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.SEARCH_RESULTS,
    getter=search_results_getter,
)


blacklist = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-users-blacklist"),
    Column(
        Select(
            text=Format("{item[label]}"),
            id="user",
            item_id_getter=lambda item: item["telegram_id"],
            items="blocked_users",
            type_factory=int,
            on_click=on_user_select,
        )
    ),
    Row(
        Button(text=Format("<"), id="prev", on_click=on_blacklist_prev, when=F["page"] > 1),
        Button(text=Format("{page}/{pages}"), id="page", on_click=on_page_info),
        Button(
            text=Format(">"),
            id="next",
            on_click=on_blacklist_next,
            when=F["page"] < F["pages"],
        ),
        when=F["show_pager"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-users-unblock-all"),
            id="unblock_all",
            on_click=on_unblock_all,
            when=F["blocked_users_exists"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardUsers.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardUsers.BLACKLIST,
    getter=blacklist_getter,
)

router = Dialog(
    users,
    all_users,
    search,
    recent_registered,
    recent_activity,
    search_results,
    blacklist,
)
