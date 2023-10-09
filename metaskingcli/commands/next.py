from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import next


def execute(args: CliArgs) -> int:
    assert args.next is not None

    json_params: dict[str, Any] = {}
    if args.next.name is not None:
        json_params['name'] = args.next.name
    if args.next.description is not None:
        json_params['description'] = args.next.description
    if args.next.task is not None:
        json_params['task'] = args.next.task
    if args.next.category is not None:
        json_params['category'] = args.next.category

    params: dict[str, Any] = {}
    if args.next.adjust is not None:
        params['adjust-time'] = args.next.adjust.total_seconds()

    next(args.server, params, **json_params)
    return 0
