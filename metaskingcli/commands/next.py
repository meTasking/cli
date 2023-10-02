from metaskingcli.args import CliArgs
from metaskingcli.api.log import next


def execute(args: CliArgs) -> int:
    next(args.server)
    return 0
