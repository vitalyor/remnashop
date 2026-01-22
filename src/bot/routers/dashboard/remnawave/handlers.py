from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button, Select

from src.bot.states import DashboardRemnawave


async def _set_page(dialog_manager: DialogManager, key: str, value: int) -> None:
    dialog_manager.dialog_data[key] = max(1, int(value))
    await dialog_manager.switch_to(state=dialog_manager.current_context().state)


async def on_page_info(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await callback.answer()


async def on_hosts_prev(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_hosts",
        int(dialog_manager.dialog_data.get("page_hosts", 1)) - 1,
    )


async def on_hosts_next(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_hosts",
        int(dialog_manager.dialog_data.get("page_hosts", 1)) + 1,
    )


async def on_nodes_prev(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_nodes",
        int(dialog_manager.dialog_data.get("page_nodes", 1)) - 1,
    )


async def on_nodes_next(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_nodes",
        int(dialog_manager.dialog_data.get("page_nodes", 1)) + 1,
    )


async def on_inbounds_prev(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_inbounds",
        int(dialog_manager.dialog_data.get("page_inbounds", 1)) - 1,
    )


async def on_inbounds_next(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    await _set_page(
        dialog_manager,
        "page_inbounds",
        int(dialog_manager.dialog_data.get("page_inbounds", 1)) + 1,
    )


async def on_host_select(
    callback: CallbackQuery,
    widget: Select[int],
    dialog_manager: DialogManager,
    selected_idx: int,
) -> None:
    dialog_manager.dialog_data["selected_host_idx"] = selected_idx
    await dialog_manager.switch_to(DashboardRemnawave.HOST)


async def on_node_select(
    callback: CallbackQuery,
    widget: Select[int],
    dialog_manager: DialogManager,
    selected_idx: int,
) -> None:
    dialog_manager.dialog_data["selected_node_idx"] = selected_idx
    await dialog_manager.switch_to(DashboardRemnawave.NODE)


async def on_inbound_select(
    callback: CallbackQuery,
    widget: Select[int],
    dialog_manager: DialogManager,
    selected_idx: int,
) -> None:
    dialog_manager.dialog_data["selected_inbound_idx"] = selected_idx
    await dialog_manager.switch_to(DashboardRemnawave.INBOUND)
