from metaskingcli.args import CliArgs
from metaskingcli.api.log import start


def execute(args: CliArgs) -> int:
    start(args.server)
    return 0
