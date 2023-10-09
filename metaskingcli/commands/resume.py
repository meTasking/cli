from typing import Any

from metaskingcli.args import CliArgs
from metaskingcli.api.log import resume


def execute(args: CliArgs) -> int:
    assert args.resume is not None

    params: dict[str, Any] = {}
    if args.resume.adjust is not None:
        params['adjust_time'] = args.resume.adjust.total_seconds()

    resume(
        args.server,
        args.resume.id if args.resume.id is not None else -1,
        **params
    )
    return 0
