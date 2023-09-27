from metaskingcli.args import CliArgs
from metaskingcli.api.log import delete


def execute(args: CliArgs) -> int:
    assert args.delete is not None
    delete(args.server, args.delete.id if args.delete.id is not None else -1)
    return 0
