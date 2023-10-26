from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import start, next


async def execute(args: CliArgs) -> int:
    assert args.start is not None

    json_params: dict[str, Any] = {}
    if args.start.name is not None:
        json_params['name'] = args.start.name
    if args.start.description is not None:
        json_params['description'] = args.start.description
    if args.start.task is not None:
        json_params['task'] = args.start.task
    if args.start.category is not None:
        json_params['category'] = args.start.category

    params: dict[str, Any] = {}
    if args.start.time is not None:
        params['override-time'] = args.start.time.isoformat()
    if args.start.adjust is not None:
        params['adjust-time'] = args.start.adjust.total_seconds()

    fn = next if args.start.next else start
    await fn(args.server, params, **json_params)
    return 0
