from metaskingcli.args import CliArgs
from metaskingcli.api.log import resume


def execute(args: CliArgs) -> int:
    assert args.resume is not None
    resume(args.server, args.resume.id if args.resume.id is not None else -1)
    return 0
