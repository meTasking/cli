from metaskingcli.args import CliArgs
from metaskingcli.api.log import pause


def execute(args: CliArgs) -> int:
    assert args.pause is not None
    pause(args.server, args.pause.id)
    return 0
