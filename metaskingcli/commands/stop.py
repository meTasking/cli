from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import stop, stop_all


def execute(args: CliArgs) -> int:
    assert args.stop is not None

    params: dict[str, Any] = {}
    if args.stop.adjust is not None:
        params['adjust-time'] = args.stop.adjust.total_seconds()

    if args.stop.all:
        stop_all(args.server, **params)
    else:
        stop(args.server, args.stop.id, **params)
    return 0
