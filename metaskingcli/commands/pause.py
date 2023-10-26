from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import pause


async def execute(args: CliArgs) -> int:
    assert args.pause is not None

    params: dict[str, Any] = {}
    if args.pause.time is not None:
        params['override-time'] = args.pause.time.isoformat()
    if args.pause.adjust is not None:
        params['adjust-time'] = args.pause.adjust.total_seconds()

    await pause(args.server, args.pause.id, **params)
    return 0
