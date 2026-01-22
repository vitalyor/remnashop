from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.kbd import Row, ScrollingGroup, Select, Start, SwitchTo
from aiogram_dialog.widgets.text import Format

from src.bot.keyboards import main_menu_button
from src.bot.states import Dashboard, DashboardRemnawave
from src.bot.widgets import Banner, I18nFormat, IgnoreUpdate
from src.core.enums import BannerName

from .getters import (
    host_getter,
    hosts_getter,
    inbound_getter,
    inbounds_getter,
    node_getter,
    nodes_getter,
    system_getter,
    users_getter,
)
from .handlers import on_host_select, on_inbound_select, on_node_select

remnawave = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-main"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-remnawave-users"),
            id="users",
            state=DashboardRemnawave.USERS,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-remnawave-hosts"),
            id="hosts",
            state=DashboardRemnawave.HOSTS,
        ),
        SwitchTo(
            text=I18nFormat("btn-remnawave-nodes"),
            id="nodes",
            state=DashboardRemnawave.NODES,
        ),
        SwitchTo(
            text=I18nFormat("btn-remnawave-inbounds"),
            id="inbounds",
            state=DashboardRemnawave.INBOUNDS,
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
    state=DashboardRemnawave.MAIN,
    getter=system_getter,
)

users = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-users"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.USERS,
    getter=users_getter,
)

hosts = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-hosts-list", count=Format("{count}")),
    ScrollingGroup(
        Select(
            text=Format("{item[label]}"),
            id="host",
            item_id_getter=lambda item: item["idx"],
            items="hosts",
            type_factory=int,
            on_click=on_host_select,
        ),
        id="hosts_scroll",
        width=1,
        height=10,
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.HOSTS,
    getter=hosts_getter,
)

host = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-hosts"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.HOSTS,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.HOST,
    getter=host_getter,
)

nodes = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-nodes-list", count=Format("{count}")),
    ScrollingGroup(
        Select(
            text=Format("{item[label]}"),
            id="node",
            item_id_getter=lambda item: item["idx"],
            items="nodes",
            type_factory=int,
            on_click=on_node_select,
        ),
        id="nodes_scroll",
        width=1,
        height=10,
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.NODES,
    getter=nodes_getter,
)

node = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-nodes"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.NODES,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.NODE,
    getter=node_getter,
)

inbounds = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-inbounds-list", count=Format("{count}")),
    ScrollingGroup(
        Select(
            text=Format("{item[label]}"),
            id="inbound",
            item_id_getter=lambda item: item["idx"],
            items="inbounds",
            type_factory=int,
            on_click=on_inbound_select,
        ),
        id="inbounds_scroll",
        width=1,
        height=10,
        hide_on_single_page=True,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.INBOUNDS,
    getter=inbounds_getter,
)

inbound = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-remnawave-inbounds"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back"),
            id="back",
            state=DashboardRemnawave.INBOUNDS,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardRemnawave.INBOUND,
    getter=inbound_getter,
)

router = Dialog(
    remnawave,
    users,
    hosts,
    host,
    nodes,
    node,
    inbounds,
    inbound,
)
