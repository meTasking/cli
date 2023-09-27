from metaskingcli.args import CliArgs
from metaskingcli.api.log import stop, stop_all


def execute(args: CliArgs) -> int:
    assert args.stop is not None
    if args.stop.all:
        stop_all(args.server)
    elif args.stop.id is not None:
        stop(args.server, args.stop.id)
    else:
        raise RuntimeError("Either --all or --id must be specified")
    return 0
