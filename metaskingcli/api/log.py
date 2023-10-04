import datetime
import requests

from .base import handle_response


API_VERSION = "v1"


def list_all(
    server: str,
    offset: int = 0,
    limit: int = 100,
    category_id: int | None = None,
    task_id: int | None = None,
    stopped: bool | None = None,
    order: str | None = None,
    since: datetime.datetime | None = None,
    until: datetime.datetime | None = None,
) -> list[dict]:
    url = f"{server}/api/{API_VERSION}/log/list"
    params: dict[str, str] = {
        "offset": str(offset),
        "limit": str(limit),
    }
    if category_id is not None:
        params["category_id"] = str(category_id)
    if task_id is not None:
        params["task_id"] = str(task_id)
    if stopped is not None:
        params["stopped"] = str(stopped)
    if order is not None:
        params["order"] = order
    if since is not None:
        params["since"] = since.isoformat()
    if until is not None:
        params["until"] = until.isoformat()
    return handle_response(requests.get(url, params=params))


def start(server: str, **kwargs) -> dict:
    url = f"{server}/api/{API_VERSION}/log/start"
    return handle_response(requests.post(url, json=kwargs))


def next(server: str) -> dict:
    url = f"{server}/api/{API_VERSION}/log/next"
    return handle_response(requests.post(url))


def stop_all(server: str) -> dict:
    url = f"{server}/api/{API_VERSION}/log/all/stop"
    return handle_response(requests.post(url))


def stop(server: str, log_id: int | None) -> dict:
    if log_id is not None:
        log_name = f"{log_id}"
    else:
        log_name = "active"
    url = f"{server}/api/{API_VERSION}/log/{log_name}/stop"
    return handle_response(requests.post(url))


def pause_active(server: str) -> dict:
    return pause(server, None)


def pause(server: str, log_id: int | None) -> dict:
    if log_id is not None:
        log_name = f"{log_id}"
    else:
        log_name = "active"
    url = f"{server}/api/{API_VERSION}/log/{log_name}/pause"
    return handle_response(requests.post(url))


def resume(server: str, log_id: int) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{log_id}/resume"
    return handle_response(requests.post(url))


def get_active(server: str) -> dict:
    return read(server, None)


def read(server: str, log_id: int | None) -> dict:
    if log_id is not None:
        log_name = f"{log_id}"
    else:
        log_name = "active"
    url = f"{server}/api/{API_VERSION}/log/{log_name}"
    return handle_response(requests.get(url))


def update(
    server: str,
    log_id: int,
    create_category: bool = False,
    create_task: bool = False,
    **kwargs,
) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{log_id}"
    params = {
        "create-category": create_category,
        "create-task": create_task,
    }
    return handle_response(requests.put(url, params=params, json=kwargs))


def delete(server: str, log_id: int) -> dict:
    url = f"{server}/api/{API_VERSION}/log/{log_id}"
    return handle_response(requests.delete(url))


def split(server: str, log_id: int, at: datetime.datetime) -> list[dict]:
    url = f"{server}/api/{API_VERSION}/log/{log_id}/split"
    return handle_response(requests.post(url, json={"at": at.isoformat()}))
