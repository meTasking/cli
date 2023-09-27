from metaskingcli.args import CliArgs
from metaskingcli.api.log import read


def execute(args: CliArgs) -> int:
    assert args.show is not None
    read(args.server, args.show.id)
    return 0
