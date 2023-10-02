from metaskingcli.args import CliArgs
from metaskingcli.api.log import stop, stop_all


def execute(args: CliArgs) -> int:
    assert args.stop is not None
    if args.stop.all:
        stop_all(args.server)
    else:
        stop(args.server, args.stop.id)
    return 0
