from typing import Any, Optional, AsyncGenerator
import datetime
import aiohttp

from .base import handle_response, API_VERSION


async def list_all(
    server: str,
    category_id: int | None = None,
    task_id: int | None = None,
    stopped: bool | None = None,
    flags: list[str] | None = None,
    order: str | None = None,
    since: datetime.datetime | None = None,
    until: datetime.datetime | None = None,
    start_offset: int = 0,
    page_limit: int = 100,
) -> AsyncGenerator[dict, None]:
    offset = start_offset
    while True:
        logs = await list_page(
            server,
            offset=offset,
            limit=page_limit,
            category_id=category_id,
            task_id=task_id,
            stopped=stopped,
            flags=flags,
            order=order,
            since=since,
            until=until,
        )
        if len(logs) == 0:
            break
        for log in logs:
            yield log
        offset += len(logs)


async def list_page(
    server: str,
    offset: int = 0,
    limit: int = 100,
    category_id: int | None = None,
    task_id: int | None = None,
    stopped: bool | None = None,
    flags: list[str] | None = None,
    order: str | None = None,
    since: datetime.datetime | None = None,
    until: datetime.datetime | None = None,
) -> list[dict]:
    url = f"{server}/api/{API_VERSION}/log/list"
    params: dict[str, Any] = {
        "offset": str(offset),
        "limit": str(limit),
    }
    if category_id is not None:
        params["category_id"] = category_id
    if task_id is not None:
        params["task_id"] = task_id
    if stopped is not None:
        params["stopped"] = "true" if stopped else "false"
    if flags is not None:
        params["flags"] = flags
    if order is not None:
        params["order"] = order
    if since is not None:
        params["since"] = since.isoformat()
    if until is not None:
        params["until"] = until.isoformat()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            return await handle_response(response)


async def start(
    server: str,
    params: Optional[dict[str, Any]] = None,
    **kwargs
) -> dict:
    url = f"{server}/api/{API_VERSION}/log/start"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, json=kwargs) as response:
            return await handle_response(response)


async def next(
    server: str,
    params: Optional[dict[str, Any]] = None,
    **kwargs
) -> dict:
    url = f"{server}/api/{API_VERSION}/log/next"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, json=kwargs) as response:
            return await handle_response(response)


async def stop_all(server: str, **kwargs) -> dict:
    url = f"{server}/api/{API_VERSION}/log/all/stop"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=kwargs) as response:
            return await handle_response(response)


async def stop_active(server: str, **kwargs) -> dict:
    return await stop(server, None, **kwargs)


async def stop(
    server: str,
    dynamic_log_id: int | None = None,
    **kwargs
) -> dict:
    if dynamic_log_id is not None:
        log_name = f"{dynamic_log_id}"
    else:
        log_name = "active"
    url = f"{server}/api/{API_VERSION}/log/{log_name}/stop"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=kwargs) as response:
            return await handle_response(response)


async def pause_active(server: str, **kwargs) -> dict:
    return await pause(server, None, **kwargs)


async def pause(server: str, log_id: int | None, **kwargs) -> dict:
    if log_id is not None:
        log_name = f"{log_id}"
    else:
        log_name = "active"
    url = f"{server}/api/{API_VERSION}/log/{log_name}/pause"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=kwargs) as response:
            return await handle_response(response)


async def resume(server: str, dynamic_log_id: int, **kwargs) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{dynamic_log_id}/resume"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=kwargs) as response:
            return await handle_response(response)


async def get_active(server: str) -> Optional[dict]:
    try:
        return await read(server, None)
    except aiohttp.ClientResponseError as e:
        if e.status == 404:
            return None
        raise


async def read(server: str, dynamic_log_id: int | None = None) -> dict:
    if dynamic_log_id is not None:
        log_name = f"{dynamic_log_id}"
    else:
        log_name = "active"
    async with aiohttp.ClientSession() as session:
        url = f"{server}/api/{API_VERSION}/log/{log_name}"
        async with session.get(url) as response:
            return await handle_response(response)


async def update(
    server: str,
    dynamic_log_id: int,
    create_category: bool = False,
    create_task: bool = False,
    **kwargs,
) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{dynamic_log_id}"
    params = {
        "create-category": "true" if create_category else "false",
        "create-task": "true" if create_task else "false",
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, params=params, json=kwargs) as response:
            return await handle_response(response)


async def update_active(
    server: str,
    create_category: bool = False,
    create_task: bool = False,
    **kwargs,
) -> dict:
    url = f"{server}/api/{API_VERSION}/log/active"
    params = {
        "create-category": "true" if create_category else "false",
        "create-task": "true" if create_task else "false",
    }
    async with aiohttp.ClientSession() as session:
        async with session.put(url, params=params, json=kwargs) as response:
            return await handle_response(response)


async def delete(server: str, dynamic_log_id: int) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{dynamic_log_id}"
    async with aiohttp.ClientSession() as session:
        async with session.delete(url) as response:
            return await handle_response(response)


async def split(
    server: str,
    dynamic_log_id: int,
    at: datetime.datetime
) -> list[dict]:
    url = f"{server}/api/{API_VERSION}/log/{dynamic_log_id}/split"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"at": at.isoformat()}) as response:
            return await handle_response(response)


async def merge(server: str, log_id: int, with_log_id: int) -> list[dict]:
    url = f"{server}/api/{API_VERSION}/log/{log_id}/merge/{with_log_id}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            return await handle_response(response)
