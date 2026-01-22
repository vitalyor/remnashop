from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Select

from src.bot.states import DashboardRemnawave


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

