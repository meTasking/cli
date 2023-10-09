from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import pause


def execute(args: CliArgs) -> int:
    assert args.pause is not None

    params: dict[str, Any] = {}
    if args.pause.adjust is not None:
        params['adjust_time'] = args.pause.adjust.total_seconds()

    pause(args.server, args.pause.id, **params)
    return 0
