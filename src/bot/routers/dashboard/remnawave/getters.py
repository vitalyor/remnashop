from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from fluentogram import TranslatorRunner
from remnapy import RemnawaveSDK

from src.core.i18n.translator import get_translated_kwargs
from src.core.utils.formatters import (
    format_country_code,
    format_percent,
    i18n_format_bytes_to_unit,
    i18n_format_seconds,
)


@inject
async def system_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    **kwargs: Any,
) -> dict[str, Any]:
    result = await remnawave.system.get_stats()

    return {
        "version": "",  # TODO: Добавить версию панели
        "cpu_cores": result.cpu.physical_cores,
        "cpu_threads": result.cpu.cores,
        "ram_used": i18n_format_bytes_to_unit(result.memory.active),
        "ram_total": i18n_format_bytes_to_unit(result.memory.total),
        "ram_used_percent": format_percent(
            part=result.memory.active,
            whole=result.memory.total,
        ),
        "uptime": i18n_format_seconds(result.uptime),
    }


@inject
async def users_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    **kwargs: Any,
) -> dict[str, Any]:
    result = await remnawave.system.get_stats()

    return {
        "users_total": str(result.users.total_users),
        "users_active": str(result.users.status_counts.get("ACTIVE")),
        "users_disabled": str(result.users.status_counts.get("DISABLED")),
        "users_limited": str(result.users.status_counts.get("LIMITED")),
        "users_expired": str(result.users.status_counts.get("EXPIRED")),
        "online_last_day": str(result.online_stats.last_day),
        "online_last_week": str(result.online_stats.last_week),
        "online_never": str(result.online_stats.never_online),
        "online_now": str(result.online_stats.online_now),
    }


@inject
async def hosts_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    result = await remnawave.hosts.get_all_hosts()

    hosts_list: list[dict[str, Any]] = []
    hosts_details: list[str] = []

    for idx, host in enumerate(result):
        hosts_list.append(
            {
                "idx": idx,
                "label": f"{'🟢' if not host.is_disabled else '🔴'} {host.remark}",
            }
        )
        hosts_details.append(
            i18n.get(
                "msg-remnawave-host-details",
                remark=host.remark,
                status="OFF" if host.is_disabled else "ON",
                address=host.address,
                port=str(host.port),
                inbound_uuid=str(host.inbound_uuid) if host.inbound_uuid else False,
            )
        )

    dialog_manager.dialog_data["hosts_details"] = hosts_details

    return {
        "count": len(hosts_list),
        "hosts": hosts_list,
    }


@inject
async def host_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    selected_idx = dialog_manager.dialog_data.get("selected_host_idx", 0)
    details: list[str] = dialog_manager.dialog_data.get("hosts_details", [])

    if not details:
        await hosts_getter(dialog_manager=dialog_manager, remnawave=remnawave, i18n=i18n)
        details = dialog_manager.dialog_data.get("hosts_details", [])

    if not details:
        return {"host": i18n.get("empty")}

    selected_idx = max(0, min(int(selected_idx), len(details) - 1))
    return {"host": details[selected_idx]}


@inject
async def nodes_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    result = await remnawave.nodes.get_all_nodes()
    nodes_list: list[dict[str, Any]] = []
    nodes_details: list[str] = []

    for idx, node in enumerate(result):
        kwargs_for_i18n = {
            "xray_uptime": i18n_format_seconds(node.xray_uptime),
            "traffic_used": i18n_format_bytes_to_unit(node.traffic_used_bytes),
            "traffic_limit": i18n_format_bytes_to_unit(
                node.traffic_limit_bytes or -1, round_up=True
            ),
        }

        translated_data = get_translated_kwargs(i18n, kwargs_for_i18n)

        country = format_country_code(code=node.country_code)
        nodes_list.append(
            {
                "idx": idx,
                "label": f"{'🟢' if node.is_connected else '🔴'} {country} {node.name}",
            }
        )
        nodes_details.append(
            i18n.get(
                "msg-remnawave-node-details",
                country=country,
                name=node.name,
                status="ON" if node.is_connected else "OFF",
                address=node.address,
                port=str(node.port) if node.port else False,
                xray_uptime=translated_data["xray_uptime"],
                users_online=str(node.users_online),
                traffic_used=translated_data["traffic_used"],
                traffic_limit=translated_data["traffic_limit"],
            )
        )

    dialog_manager.dialog_data["nodes_details"] = nodes_details

    return {
        "count": len(nodes_list),
        "nodes": nodes_list,
    }

@inject
async def node_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    selected_idx = dialog_manager.dialog_data.get("selected_node_idx", 0)
    details: list[str] = dialog_manager.dialog_data.get("nodes_details", [])

    if not details:
        await nodes_getter(dialog_manager=dialog_manager, remnawave=remnawave, i18n=i18n)
        details = dialog_manager.dialog_data.get("nodes_details", [])

    if not details:
        return {"node": i18n.get("empty")}

    selected_idx = max(0, min(int(selected_idx), len(details) - 1))
    return {"node": details[selected_idx]}


@inject
async def inbounds_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    result = await remnawave.inbounds.get_all_inbounds()
    inbounds_list: list[dict[str, Any]] = []
    inbounds_details: list[str] = []

    for idx, inbound in enumerate(result.inbounds):  # type: ignore[attr-defined]
        label_parts = [inbound.tag]
        if getattr(inbound, "port", None):
            label_parts.append(f":{int(inbound.port)}")
        inbounds_list.append(
            {
                "idx": idx,
                "label": " ".join(label_parts),
            }
        )
        inbounds_details.append(
            i18n.get(
                "msg-remnawave-inbound-details",
                inbound_id=str(inbound.uuid),
                tag=inbound.tag,
                type=inbound.type,
                port=str(int(inbound.port)) if inbound.port else False,
                network=inbound.network or False,
                security=inbound.security or False,
            )
        )

    dialog_manager.dialog_data["inbounds_details"] = inbounds_details

    return {
        "count": len(inbounds_list),
        "inbounds": inbounds_list,
    }

@inject
async def inbound_getter(
    dialog_manager: DialogManager,
    remnawave: FromDishka[RemnawaveSDK],
    i18n: FromDishka[TranslatorRunner],
    **kwargs: Any,
) -> dict[str, Any]:
    selected_idx = dialog_manager.dialog_data.get("selected_inbound_idx", 0)
    details: list[str] = dialog_manager.dialog_data.get("inbounds_details", [])

    if not details:
        await inbounds_getter(dialog_manager=dialog_manager, remnawave=remnawave, i18n=i18n)
        details = dialog_manager.dialog_data.get("inbounds_details", [])

    if not details:
        return {"inbound": i18n.get("empty")}

    selected_idx = max(0, min(int(selected_idx), len(details) - 1))
    return {"inbound": details[selected_idx]}
